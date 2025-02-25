import os
import re
import asyncio
import aiofiles
import numpy as np
from ollama import embeddings
from utils.logger import Logger
from config.settings import Mode
from chatbot.helper import PromptHelper
from config.settings import EMBEDDING_MODEL
from chatbot.deployer import ChatBotDeployer
from sklearn.metrics.pairwise import cosine_similarity

logger = Logger.get_logger()

helper, filter_helper = ChatBotDeployer.deploy_chatbot(Mode.HELPER)

class Topic:
    def __init__(self,name= "", description = "") -> None:
        """
        Initializes a Topic with a name and description.
        The description is embedded and cached for matching.
        
        Args:
            name (str): The topic name.
            description (str): A textual description of the topic.
        """
        self.name = name
        self.description = description
        self.embedded_description = np.array([])
        self.history: list[dict[str, str]] = []
        self.history_embeddings = [] 
        self.file_embeddings: dict[str, np.ndarray] = {}
        self.embedding_cache: dict[str, np.ndarray] = {}
        self.folder_structure: dict = {}
        self.char_limit = 5000

    def add_message(self, role, message, embedding):
        """Stores raw messages and their embeddings."""
       
        self.history.append({"role": role, "content": message})
        self.history_embeddings.append(embedding)
        #logger.info(f"Embedding shape {embedding.shape}")
        logger.info(f"Message added to {self.name}")
        
    
   
    async def get_relevant_context(self, query: str) -> tuple[float, int]:
        """
        Retrieves the best similarity score and the index of the most relevant message
        from the topic’s history based on cosine similarity.

        Args:
            query (str): The query text.
            similarity_threshold (float): The base similarity threshold (not used for slicing here).

        Returns:
            tuple[float, int]: A tuple containing:
                - The best similarity score.
                - The index of the best matching message (or -1 if not found).
        """
        logger.debug(f"Fetching relevant context for query(topic): {query}")

        if not self.history_embeddings:
            logger.info("No history embeddings found. Returning empty context.")
            return 0.0, -1

        query_embedding = await self.async_fetch_embedding(query)
        if query_embedding is None or len(query_embedding) == 0:
            logger.error("Query embedding failed.")
            return 0.0, -1

        similarities = cosine_similarity([query_embedding], self.history_embeddings)[0]
        best_index = int(np.argmax(similarities))
        best_similarity = float(similarities[best_index])
        logger.debug(f"Best similarity score: {best_similarity} at index {best_index}")
        
        return best_similarity, best_index





    
    async def get_relevant_files(self, query: str, top_k: int = 1, similarity_threshold: float = 0.66) -> list[tuple[str, str]]:
        """
        Retrieves files relevant to the query. First, it attempts to match the query with file paths
        (using a case-insensitive substring match). If any direct matches are found, those files are returned.
        If no full path matches are found, it then checks if the query matches only the file name.
        Otherwise, it computes the embedding for the query and matches it against the stored file embeddings 
        using cosine similarity.
        
        Args:
            query (str): The query text.
            top_k (int): Maximum number of files to retrieve.
            similarity_threshold (float): Minimum similarity required.
        
        Returns:
            list[tuple[str, str]]: List of (file_path, file_content) tuples.
        """
        # First: try to match query against file paths directly
        normalized_query = query.lower()
        direct_matches = [fp for fp in self.file_embeddings.keys() if normalized_query in fp.lower()]
        
        relevant_files = []
        if direct_matches:
            tasks = [self._read_file(fp) for fp in direct_matches[:top_k]]
            results = await asyncio.gather(*tasks)
            for file_path, content in results:
                if content:
                    relevant_files.append((file_path, content))
            if relevant_files:
                return relevant_files
        
        # Second: check for matches in file names
        filename_matches = [fp for fp in self.file_embeddings.keys() if normalized_query in os.path.basename(fp).lower()]
        
        if filename_matches:
            tasks = [self._read_file(fp) for fp in filename_matches[:top_k]]
            results = await asyncio.gather(*tasks)
            for file_path, content in results:
                if content:
                    relevant_files.append((file_path, content))
            if relevant_files:
                return relevant_files
        
        # Fallback: use cosine similarity on embeddings
        if not self.file_embeddings:
            return []
        
        query_embedding = await self.async_fetch_embedding(query)
        file_paths = list(self.file_embeddings.keys())
        file_embeddings = list(self.file_embeddings.values())
        similarities = cosine_similarity([query_embedding], file_embeddings)[0]
        
        # Get indices of top_k files by similarity (in descending order)
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        tasks = []
        for i in top_indices:
            if similarities[i] >= similarity_threshold:
                tasks.append(self._read_file(file_paths[i]))
        if tasks:
            results = await asyncio.gather(*tasks)
            for file_path, content in results:
                if content:
                    relevant_files.append((file_path, content))
        return relevant_files


    async def _read_file(self, file_path: str) -> tuple[str, str]:
        """
        Asynchronously reads a file.
        
        Args:
            file_path (str): The file's path.
        
        Returns:
            tuple[str, str]: The file path and its content.
        """
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = await f.read()
            return file_path, content
        except (IOError, OSError) as e:
            logger.error(f"Topic '{self.name}': Error reading file {file_path}: {str(e)}")
            return file_path, ""

    def _add_file(self, file_path: str, embedding: np.ndarray) -> None:
        """
        Internal method to add a file's embedding to the topic.
        
        Args:
            file_path (str): The file's path.
            content (str): The file content.
            embedding (np.ndarray): Pre-computed embedding of the content.
        """
        self.file_embeddings[file_path] = embedding
        logger.debug(f"Topic '{self.name}': Added file {file_path}")

    def _fetch_embedding(self, text: str) -> np.ndarray:
        """
        Synchronously fetches and caches an embedding for the given text.
        """
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        try:
            logger.info("Fetching embeddings (from topic)")
            response = embeddings(model=EMBEDDING_MODEL, prompt=text)
            embedding = response['embedding']
            self.embedding_cache[text] = embedding
            logger.debug(f"Extracted {len(embedding)} embeddings")
            return embedding
        except Exception as e:
            logger.error(f" Error fetching embedding for text: {text}. Error: {str(e)}")
            return np.array([])

    async def async_fetch_embedding(self, text: str) -> np.ndarray:
        """
        Asynchronously fetches and caches an embedding for the given text.
        """
        embedding = await asyncio.to_thread(self._fetch_embedding, text)

        return embedding


class HistoryManager:
    def __init__(self, top_k: int = 2, similarity_threshold: float = 0.6) -> None:
        """
        Initializes HistoryManager to handle topics and off-topic tracking.
        An "unsorted" topic collects messages and files until a clear topic emerges.
        
        Args:
            top_k (int): Maximum number of context items to retrieve.
            similarity_threshold (float): Threshold for determining similarity.
        """
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.topics: list[Topic] = []
        self.current_topic = Topic()
        self.embedding_cache: dict[str, np.ndarray] = {}


    async def add_message(self, role, message) -> None:
        """
        Routes a new message to the best-matching topic.
        If no topic meets the similarity threshold, the message is added to the unsorted topic.

        Args:
            role (str): Sender's role.
            message (str): The message text.
        """
        message_embedding = await self.async_fetch_embedding(message)

        if len(self.topics) != 0:
        
            matched_topic = await self._match_topic(message_embedding)
            if matched_topic:
                logger.info(f"Message matched with topic: {matched_topic.name}")
                matched_topic.add_message(role, message, message_embedding)
        else:
        
            logger.info("Message did not match any topic; adding to Current topic.")
            self.current_topic.add_message(role, message,message_embedding)
        asyncio.create_task(self._analyze_history())

    
    async def _match_topic(self, embedding: np.ndarray, exclude_topic: Topic | None = None) -> Topic | None:
        """
        Matches a message or file embedding to the most similar topic based on the description embedding,
        optionally excluding a specified topic.

        Args:
            embedding (np.ndarray): The embedding to match.
            exclude_topic (Topic | None): A topic to exclude from matching (e.g. the current topic).

        Returns:
            Topic | None: The best matching topic if similarity exceeds the threshold.
        """
        # Early exit if no topics are available.
        if len(self.topics) == 0:
            logger.info("No topics available for matching. Returning None.")
            return None

        async def compute_similarity(topic: Topic) -> tuple[float, Topic]:
            if len(topic.embedded_description) == 0 or len(embedding) == 0:
                return 0.0, topic
            similarity = cosine_similarity([embedding], [topic.embedded_description])[0][0]
            logger.debug(f"Computed similarity {similarity:.4f} for topic '{topic.name}'")
            return similarity, topic

        # Exclude the specified topic from matching.
        tasks = [compute_similarity(topic) for topic in self.topics if topic != exclude_topic]
        results = await asyncio.gather(*tasks)
        
        best_topic = None
        best_similarity = 0.0
        for similarity, topic in results:
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_topic = topic

        if best_topic:
            logger.info(f"Best matching topic: '{best_topic.name}' with similarity {best_similarity:.4f}")
        else:
            logger.info("No suitable topic found.")
        return best_topic


    async def add_file(self, file_path: str, content: str) -> None:
        """
        Adds a file by computing its embedding and routing it to the best matching topic.
        If no topic matches, the file is added to the unsorted topic. Additionally, if the file
        appears to be code and the unsorted topic lacks conversation, it is evaluated for conversion
        into a project topic.

        Args:
            file_path (str): The file's path.
            content (str): The file content.
        """
        file_embedding = await self.async_fetch_embedding(content)  # Ensure embedding function is async
        matched_topic = await self._match_topic(file_embedding)
        if matched_topic:
            logger.info(f"File '{file_path}' matched with topic: {matched_topic.name}")
            matched_topic._add_file(file_path, file_embedding)
        else:
            logger.info(f"File '{file_path}' did not match any topic; adding to unsorted topic.")
            self.current_topic._add_file(file_path, file_embedding)
            asyncio.create_task(self.get_file_tags(content))


    async def get_file_tags(self,content):
        response = await helper._fetch_response(PromptHelper.metadata_code(content))
                      
        await filter_helper.process_static(response)
        response = helper.last_response
        logger.info(f"METADATA {response}")


    def add_folder_structure(self, structure,topic_name= None) -> None:
        """
        Adds or updates folder structure.
        If topic_name is provided, the folder structure is applied to that topic;
        otherwise, it is applied to the unsorted topic.
        
        Args:
            structure (dict): The folder structure.
            topic_name (str | None): Optional topic name.
        """
        if topic_name:
            topic_name.folder_structure = structure                
            logger.info(f"Folder structure updated for topic: {topic_name}")
            return

        logger.warning(f"Topic '{topic_name}' not found. Applying folder structure to unsorted topic.")
        self.current_topic.folder_structure = structure
        logger.info("Folder structure updated for unsorted topic.")

 
    async def get_relevant_topic(self, query: str):
        """
        Asynchronously retrieves the best matching topic based on similarity score.
        For the best topic meeting the dynamic threshold, it slices the topic's history
        around the best matching message (from 5 messages before to 5 messages after).
        If a new (better) topic is found, it updates the current topic—moving the previous
        one into the topics list if not already present. If no relevant topic is found,
        it tries to retrieve similar messages within the current topic; failing that, it returns
        the last 10 messages from the current topic's history.

        Args:
            query (str): The user query.

        Returns:
            list[dict[str, str]]: A slice of the topic's history as the context.
        """
        best_score = self.similarity_threshold
        best_topic = None
        best_index = -1

        if len(self.current_topic.history) < 11:
            return self.current_topic.history

        # Iterate over all topics including the current topic.
        for topic in self.topics + [self.current_topic]:
            logger.info(f"Processing topic: {topic.name}")
            score, index = await topic.get_relevant_context(query)
            logger.debug(f"Topic '{topic.name}' returned score {score:.4f} at index {index}")
            
            # Dynamic threshold adjusts based on query length.
            dynamic_threshold = self.similarity_threshold * (len(query.split()) / 10)
            if score >= dynamic_threshold and score > best_score:
                best_score = score
                best_topic = topic
                best_index = index

        if best_topic is not None and best_index != -1:
            logger.info(f"Best matching topic: '{best_topic.name}' with score {best_score:.4f} at index {best_index}")
            start_index = max(0, best_index - 5)
            end_index = min(len(best_topic.history), best_index + 6)
            context_slice = best_topic.history[start_index:end_index]
            
            # If the best topic is not the current one, update accordingly.
            if best_topic.name != self.current_topic.name:
                # Append the current topic to the topics list if not already present.
                if not any(t.name == self.current_topic.name for t in self.topics):
                    self.topics.append(self.current_topic)
                self.current_topic = best_topic
            
            return context_slice
        else:
            logger.warning("No relevant topic found with high similarity.")
            # Fallback: attempt to get similar messages within the current topic.
            fallback_score, fallback_index = await self.current_topic.get_relevant_context(query)
            dynamic_threshold = self.similarity_threshold * (len(query.split()) / 10)
            if fallback_index != -1 and fallback_score >= dynamic_threshold:
                start_index = max(0, fallback_index - 5)
                end_index = min(len(self.current_topic.history), fallback_index + 6)
                return self.current_topic.history[start_index:end_index]
            
            # Final fallback: return the last 10 messages.
            return self.current_topic.history[-10:]
   
    async def get_relevant_files(self, query: str, top_k: int = 1, similarity_threshold: float = 0.36) -> list[tuple[str, str]]:
        """
        Retrieves relevant files by prioritizing file path and file name matches before 
        falling back to topic-based retrieval.

        Args:
            query (str): The query text.
            top_k (int): Maximum number of files to retrieve.

        Returns:
            list[tuple[str, str]]: List of (file_path, file_content) tuples.
        """

        # **Step 1: Direct file path match (prioritized)**
        normalized_query = query.lower()
        direct_matches = [fp for fp in self.current_topic.file_embeddings.keys() if normalized_query in fp.lower()]
        
        if direct_matches:
            logger.info(f"Direct file path match found for query: {query}")
            tasks = [self.current_topic._read_file(fp) for fp in direct_matches[:top_k]]
            results = await asyncio.gather(*tasks)
            return [(fp, content) for fp, content in results if content]

        # **Step 2: Check for file name matches (if query matches only the filename)**
        filename_matches = [
            fp for fp in self.current_topic.file_embeddings.keys() if normalized_query in os.path.basename(fp).lower()
        ]
        
        if filename_matches:
            logger.info(f"File name match found for query: {query}")
            tasks = [self.current_topic._read_file(fp) for fp in filename_matches[:top_k]]
            results = await asyncio.gather(*tasks)
            return [(fp, content) for fp, content in results if content]

        # **Step 3: Match query to a topic using embeddings**
        query_embedding = await self.async_fetch_embedding(query)
        matched_topic = None
        best_similarity = 0.0

        for topic in self.topics:
            if not topic.embedded_description:
                continue
            similarity = cosine_similarity([query_embedding], [topic.file_embeddings])[0][0]
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                matched_topic = topic

        # **Step 4: Retrieve files from the matched topic or unsorted topic**
        if matched_topic:
            logger.info(f"Query matched with topic: {matched_topic.name} for file retrieval.")
            return await matched_topic.get_relevant_files(query, top_k, similarity_threshold)
        
        logger.info("No matching topic for files; using unsorted topic files.")
        return await self.current_topic.get_relevant_files(query, top_k, similarity_threshold)



    def _fetch_embedding(self, text: str) -> np.ndarray:
        """
        Synchronously fetches and caches an embedding for the given text.
        """
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        try:
            logger.info("Fetching embeddings (from topic)")
            response = embeddings(model=EMBEDDING_MODEL, prompt=text)
            embedding = response['embedding']
            self.embedding_cache[text] = embedding
            logger.debug(f"Extracted {len(embedding)} embeddings")
            return embedding
        except Exception as e:
            logger.error(f" Error fetching embedding for text: {text}. Error: {str(e)}")
            return np.array([])

    async def async_fetch_embedding(self, text: str) -> np.ndarray:
        """
        Asynchronously fetches and caches an embedding for the given text.
        """
        embedding = await asyncio.to_thread(self._fetch_embedding, text)

        return embedding


    async def generate_prompt(self, query):
        """
        Generates a prompt by retrieving context and file references from the best matching topic.
        
        Args:
            query (str): The user query.
        
        Returns:
            str: The generated prompt.
        """
        
        logger.info(f"Generating prompt for query: {query}")
        relevant_topic = await self.get_relevant_topic(query)
        relevant_files = await self.get_relevant_files(query)
        file_references = ""
        for file_path, content in relevant_files:
            file_references += f"\n[Referenced File: {file_path}]\n{content[:self.current_topic.char_limit]}\n..."
        prompt = f"{query}\n\n{file_references}" if file_references else query

        logger.info(f"Generated prompt: {prompt}")
        await self.add_message("user",prompt)

        relevant_topic.append({"role": "user", "content": prompt})
        return relevant_topic


    async def generate_topic_info_from_history(self,history, max_retries: int = 3):
        """
        Attempts to extract a topic name and description from the given history.
        
        Args:
            history (list): List of unsorted history messages.
            max_retries (int): Maximum number of attempts.
            
        Returns:
            tuple: (extracted_topic_name, extracted_topic_description) if successful; otherwise (None, None).
        """
        attempt = 0
        extracted_topic_name = None
        extracted_topic_description = None

        while attempt < max_retries:
            try:
                response = await helper._fetch_response(PromptHelper.topics_helper(history))
                response = response.strip("`").strip("json")
                if not response:
                    raise ValueError("Received empty response from the helper.")
                
                await filter_helper.process_static(response)
                response = helper.last_response
                if not response:
                    raise ValueError("Response empty after filtering.")

                logger.debug(f"Extracting topic info from response: {response}")
                clean_response = re.sub(r"^```|```$|json", "", response, flags=re.IGNORECASE).strip()
                matches = re.findall(r':\s*"([^"]+)"', clean_response)
                extracted_topic_name = matches[0] if len(matches) > 0 else "unknown"
                extracted_topic_description = matches[1] if len(matches) > 1 else ""
                
                if extracted_topic_name and extracted_topic_description:
                    logger.info(f"Extracted topic: {extracted_topic_name}")
                    return extracted_topic_name, extracted_topic_description
                else:
                    raise ValueError("Could not extract valid topic information.")
            except Exception as e:
                logger.error(f"Analyze history attempt {attempt + 1} failed: {str(e)}", exc_info=True)
                attempt += 1
                if attempt < max_retries:
                    logger.info(f"Retrying analysis... (Attempt {attempt + 1} of {max_retries})")
                else:
                    logger.warning("Max analysis retries reached; not splitting unsorted history.")
                    break
        return None, None

    async def _analyze_history(self) -> None:
        """
        Analyzes the current topic's history for potential off-topic drift.
        When the history length reaches a multiple of 10, the method:
          1. Takes a slice of the last 10 messages and generates candidate topic info.
          2. Compares the candidate topic's embedding to the current topic's embedded description
             using cosine similarity (threshold 0.7).
          3. If the candidate slice is off-topic (similarity < 0.7), it then checks progressively
             smaller slices (starting with the last two messages) to determine the precise start
             of the off-topic segment.
          4. Once identified, it attempts to match the candidate embedding with an existing topic
             (excluding the current topic). If a match is found, the off-topic messages are reassigned;
             otherwise, a new topic is created.
          5. Finally, the off-topic messages are removed from the current topic.
        """
        # If the current topic is unnamed but has > 3 messages, generate a topic name/description.
        if len(self.current_topic.history) > 3 and not self.current_topic.name.strip():
            new_topic_name, new_topic_desc = await self.generate_topic_info_from_history(self.current_topic.history)
            if new_topic_name and new_topic_desc:
                self.current_topic.name = new_topic_name
                self.current_topic.description = new_topic_desc
                self.current_topic.embedded_description = await self.async_fetch_embedding(new_topic_desc)
        
        # Only trigger analysis when history length is a multiple of 10 (e.g. 10, 20, 30, …)
        if len(self.current_topic.history) >= 10 and (len(self.current_topic.history) % 10 == 0):
            logger.info("Analyzing current topic for potential off-topic segments.")
            
            # Take a candidate slice from the end – for example, the last 10 messages.
            candidate_slice = self.current_topic.history[-10:]
            candidate_topic_name, candidate_topic_desc = await self.generate_topic_info_from_history(candidate_slice)
            if candidate_topic_name and candidate_topic_desc:
                candidate_embedding = await self.async_fetch_embedding(candidate_topic_desc)
                if candidate_embedding is not None and candidate_embedding.any():
                    # Compute similarity between candidate slice embedding and current topic's embedded description.
                    sim_to_current = cosine_similarity([candidate_embedding], [self.current_topic.embedded_description])[0][0]
                    logger.debug(f"Candidate slice similarity to current topic: {sim_to_current:.4f}")
                    
                    if sim_to_current < 0.7:
                        # Off-topic drift detected in the candidate slice.
                        # Narrow down the off-topic segment by testing smaller slices.
                        off_topic_start_index = len(self.current_topic.history) - 10  # initial candidate start.
                        
                        # Iterate from last 2 messages up to the full candidate slice.
                        for i in range(2, 11):
                            test_slice = self.current_topic.history[-i:]
                            test_topic_name, test_topic_desc = await self.generate_topic_info_from_history(test_slice)
                            if test_topic_name and test_topic_desc:
                                test_embedding = await self.async_fetch_embedding(test_topic_desc)
                                if test_embedding is not None and test_embedding.any():
                                    test_sim = cosine_similarity([test_embedding], [self.current_topic.embedded_description])[0][0]
                                    logger.debug(f"Testing last {i} messages: similarity = {test_sim:.4f}")
                                    if test_sim >= 0.7:
                                        # Found a slice that is still on-topic; thus, the off-topic segment likely starts
                                        # right after this slice.
                                        off_topic_start_index = len(self.current_topic.history) - i + 1
                                        break
                        # Slice the off-topic segment.
                        off_topic_segment = self.current_topic.history[off_topic_start_index:]
                        logger.info(f"Identified off-topic segment from index {off_topic_start_index} to end (total {len(off_topic_segment)} messages).")
                        
                        # Attempt to match the candidate embedding with an existing topic, excluding the current topic.
                        matched_topic = await self._match_topic(candidate_embedding, exclude_topic=self.current_topic)
                        if matched_topic is not None:
                            for msg in off_topic_segment:
                                msg_emb = await self.async_fetch_embedding(msg["content"])
                                if msg_emb is not None and msg_emb.any():
                                    matched_topic.add_message(msg["role"], msg["content"], msg_emb)
                            logger.info(f"Reassigned off-topic segment of {len(off_topic_segment)} messages to existing topic '{matched_topic.name}'.")
                        else:
                            # No matching topic found – create a new topic.
                            try:
                                new_topic = Topic(candidate_topic_name, candidate_topic_desc)
                                new_topic.embedded_description = candidate_embedding
                                for msg in off_topic_segment:
                                    msg_emb = await self.async_fetch_embedding(msg["content"])
                                    if msg_emb is not None and msg_emb.any():
                                        new_topic.add_message(msg["role"], msg["content"], msg_emb)
                                self.topics.append(new_topic)
                                logger.info(f"Created new topic '{new_topic.name}' with {len(off_topic_segment)} off-topic messages.")
                            except Exception as e:
                                logger.error(f"Error creating new topic from off-topic messages: {e}", exc_info=True)
                        
                        # Remove off-topic messages from the current topic.
                        self.current_topic.history = self.current_topic.history[:off_topic_start_index]

