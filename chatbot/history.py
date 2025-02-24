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
       
        self.history.append({"role": role, "message": message})
        self.history_embeddings.append(embedding)
        logger.info(f"Message added to {self.name}")
        
    async def get_relevant_context(self, query: str, top_k: int = 2, similarity_threshold: float = 0.42) -> tuple[float, str, str]:
        """
        Retrieves relevant context based on the query using cosine similarity, dynamically adjusting threshold.
        If no relevant messages meet the threshold, returns the last 10 messages from history.

        Returns:
            tuple[float, str, str]: A tuple containing:
                - The similarity score.
                - The context string.
                - The topic name.
        """
        logger.debug(f"Fetching relevant context for query(topic): {query}")

        if not self.history and not self.folder_structure:
            logger.info("No history or folder structure available.")
            return 0.0, "", self.name

        context_parts = []
        similarity_scores = []
        # If history embeddings are available, find relevant messages
        if self.history_embeddings:
            query_embedding = await self.async_fetch_embedding(query)
            if query_embedding is None or len(query_embedding) == 0:
                logger.error("Query embedding failed.")
                return 0.0, "", self.name
            # Calculate similarities with history embeddings
            similarities = cosine_similarity([query_embedding], self.history_embeddings)[0]

            # Calculate dynamic threshold based on query length
            dynamic_threshold = similarity_threshold * len(query.split()) / 10

            # Get top-k relevant messages above the dynamic threshold
            relevant_messages = [
                (f"Role: {self.history[i]['role']} Message: {self.history[i]['message']}", similarities[i])
                for i in range(len(similarities))
                if similarities[i] >= dynamic_threshold
            ][:top_k]

            # If there are relevant messages, append them and their similarities
            if relevant_messages:
                for message, score in relevant_messages:
                    context_parts.append(message)
                    similarity_scores.append(score)

        # If folder structure is available, add it to context
        if self.folder_structure:
            context_parts.append(f"Folder Structure:\n{self.folder_structure}")

        # If no relevant context found, use the last 10 messages from history
        if not context_parts:
            logger.info("No relevant context found. Using last 10 messages from history.")
            last_messages = self.history[-10:]  # Get the last 10 messages
            return 0.0, "\n".join(f"Role: {msg['role']} Message: {msg['message']}" for msg in last_messages), self.name

        # Calculate average similarity score from relevant messages
        avg_score = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0.0

        # Combine the relevant context and return the score
        return avg_score, "\n".join(context_parts), self.name




    
    async def get_relevant_files(self, query: str, top_k: int = 1, similarity_threshold: float = 0.45) -> list[tuple[str, str]]:
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
    def __init__(self, top_k: int = 2, similarity_threshold: float = 0.48) -> None:
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
        self.unsorted_topic = Topic()
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
        
            logger.info("Message did not match any topic; adding to unsorted topic.")
            self.unsorted_topic.add_message(role, message,message_embedding)
        asyncio.create_task(self._evaluate_topics())

    async def _match_topic(self, embedding: np.ndarray) -> Topic | None:
        """
        Matches a message or file embedding to the most similar topic based on the description embedding.
        
        Args:
            embedding (np.ndarray): The embedding to match.
        
        Returns:
            Topic | None: The best matching topic if similarity exceeds the threshold.
        """
        async def compute_similarity(topic: Topic) -> tuple[float, Topic]:
            if len(topic.embedded_description) == 0 or len(embedding) == 0:
                return 0.0, topic
            similarity = cosine_similarity([embedding], [topic.embedded_description])[0][0]
            logger.debug(f"Computed similarity {similarity:.4f} for topic '{topic.name}'")
            return similarity, topic

        tasks = [compute_similarity(topic) for topic in self.topics]
        results = await asyncio.gather(*tasks)
        
        best_topic = None
        best_similarity = 0.0
        for similarity, topic in results:
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_topic = topic
    
        logger.info(f"Best matching topic: '{best_topic.name}' with similarity {best_similarity:.4f}" if best_topic else "No suitable topic found.")
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
            self.unsorted_topic._add_file(file_path, file_embedding)
         

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
        self.unsorted_topic.folder_structure = structure
        logger.info("Folder structure updated for unsorted topic.")

   
    
    async def get_relevant_context(self, query: str) -> str | None:
        """
        Asynchronously retrieves context from each topic sequentially and selects
        the topic with the highest similarity score. Falls back to the unsorted topic
        if no topic meets the threshold.
        
        Args:
            query (str): The user query.
        
        Returns:
            str | None: The combined context string.
        """
        if len(self.topics) == 0:
            logger.info("Returning history as context")
            return "\n".join([f"{entry['role']}: {entry['message']}" for entry in self.unsorted_topic.history])

        best_score = self.similarity_threshold
        best_context = None
        best_topic_name = None

        # Iterate over all topics (including unsorted) one by one.
        for topic in self.topics + [self.unsorted_topic]:
            logger.info(f"Processing topic: {topic.name}")
            score, context, topic_name = await topic.get_relevant_context(
                query, self.top_k, self.similarity_threshold
            )
            logger.debug(f"Topic '{topic.name}' returned score {score:.4f} with context: {context}")
            if context and score > best_score:
                best_score = score
                best_context = context
                best_topic_name = topic_name

        if best_context:
            logger.info(f"Best matching topic: '{best_topic_name}' with score {best_score:.4f}")
            return f"Topic: {best_topic_name}\n{best_context}"
        else:
            logger.warning("No matching topic found; falling back to unsorted topic.")
            # Fallback: use unsorted topic's asynchronous context.
            score, context, topic_name = await self.unsorted_topic.get_relevant_context(
                query, self.top_k, self.similarity_threshold
            )
            return f"Topic: {self.unsorted_topic.name}\n{context}" if context else None


   
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
        direct_matches = [fp for fp in self.unsorted_topic.file_embeddings.keys() if normalized_query in fp.lower()]
        
        if direct_matches:
            logger.info(f"Direct file path match found for query: {query}")
            tasks = [self.unsorted_topic._read_file(fp) for fp in direct_matches[:top_k]]
            results = await asyncio.gather(*tasks)
            return [(fp, content) for fp, content in results if content]

        # **Step 2: Check for file name matches (if query matches only the filename)**
        filename_matches = [
            fp for fp in self.unsorted_topic.file_embeddings.keys() if normalized_query in os.path.basename(fp).lower()
        ]
        
        if filename_matches:
            logger.info(f"File name match found for query: {query}")
            tasks = [self.unsorted_topic._read_file(fp) for fp in filename_matches[:top_k]]
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
        return await self.unsorted_topic.get_relevant_files(query, top_k, similarity_threshold)



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


    async def generate_prompt(self, query) -> str:
        """
        Generates a prompt by retrieving context and file references from the best matching topic.
        
        Args:
            query (str): The user query.
        
        Returns:
            str: The generated prompt.
        """
        
        logger.info(f"Generating prompt for query: {query}")
        context = await self.get_relevant_context(query)
        relevant_files = await self.get_relevant_files(query)
        file_references = ""
        for file_path, content in relevant_files:
            file_references += f"\n[Referenced File: {file_path}]\n{content[:self.unsorted_topic.char_limit]}\n..."
        prompt = f"Context:\n{context}\n\nUser Query: {query}\n\n{file_references}" if context or file_references else query
        logger.info(f"Generated prompt: {prompt}")
        return prompt


    
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

    # --------------------- Helper Methods --------------------- #

    async def _analyze_unsorted_history(self) -> None:
        """
        If unsorted_topic has at least 10 messages, attempt to generate a new topic
        from its history using the helper function.
        """
        if len(self.unsorted_topic.history) >= 10:
            logger.info("Attempting to analyze unsorted history for potential topic splitting.")
            new_topic_name, new_topic_desc = await self.generate_topic_info_from_history(self.unsorted_topic.history)
            if new_topic_name and new_topic_desc:
                try:
                    new_topic = Topic(new_topic_name, new_topic_desc)
                    new_topic.embedded_description = await self.async_fetch_embedding(new_topic_desc)
                    for msg in self.unsorted_topic.history.copy():
                        embedding = await self.async_fetch_embedding(msg["message"])
                        if embedding is None or len(embedding) == 0:
                            continue
                        similarity = cosine_similarity([embedding], [new_topic.embedded_description])[0][0]
                        if similarity >= self.similarity_threshold:
                            new_topic.add_message(msg["role"], msg["message"], embedding)
                            self.unsorted_topic.history.remove(msg)
                    if new_topic.history:
                        self.topics.append(new_topic)
                        logger.info(f"Created new topic '{new_topic_name}' from unsorted history after analysis.")
                except Exception as e:
                    logger.error(f"Error creating new topic from unsorted messages: {e}", exc_info=True)

    async def _reevaluate_topics_off_messages(self) -> None:
        """
        Reevaluate each topic's messages. If a message's similarity to its current topic
        is below the threshold, try to reassign it to a better-fitting topic or move it to unsorted_topic.
        """
        if len(self.topics) > 4:
            for topic in self.topics:
                if not topic.history or len(topic.history) < 20:
                    continue
                for msg in topic.history.copy():
                    embedding = await self.async_fetch_embedding(msg["message"])
                    if embedding is None or len(embedding) == 0:
                        continue
                    current_similarity = (cosine_similarity([embedding], [topic.embedded_description])[0][0]
                                          if topic.embedded_description is not None and len(topic.embedded_description) > 0
                                          else 0.0)
                    if current_similarity < self.similarity_threshold:
                        new_topic = await self._match_topic(embedding)
                        if new_topic is not None and new_topic != topic:
                            new_topic.add_message(msg["role"], msg["message"], embedding)
                            topic.history.remove(msg)
                            logger.info(f"Reassigned message from topic '{topic.name}' to '{new_topic.name}'.")
                        elif new_topic is None:
                            self.unsorted_topic.add_message(msg["role"], msg["message"], embedding)
                            topic.history.remove(msg)
                            logger.info(f"Moved message from topic '{topic.name}' to unsorted_topic due to low similarity.")

    async def _reassign_topic_names(self) -> None:
        """
        For topics with auto-generated names that now have accumulated messages,
        reassign a new name, description, and description embedding using the helper function.
        """
        for topic in self.topics:
            if topic.name in ["Auto-generated topic", "Auto-generated file topic"] and topic.history:
                logger.info(f"Attempting to reassign name for topic with auto-generated name (contains {len(topic.history)} messages).")
                new_name, new_description = await self.generate_topic_info_from_history(topic.history)
                if new_name and new_description:
                    topic.name = new_name
                    topic.description = new_description
                    topic.embedded_description = await self.async_fetch_embedding(new_description)
                    logger.info(f"Reassigned topic name to '{new_name}'.")

    # --------------------- Main Evaluation Function --------------------- #

    async def _evaluate_topics(self) -> None:
        """
        Main evaluation function that orchestrates topic evaluation by calling helper steps:
          1. Analyze unsorted history for potential topic splitting.
          2. Process unsorted_topic messages and file embeddings.
          3. Reevaluate each topic for off-topic messages.
          4. Reassign topic names for auto-generated topics.
        """
        logger.info(f"Current number of topics: {len(self.topics)}")
        await self._analyze_unsorted_history()
        await self._reevaluate_topics_off_messages()
        await self._reassign_topic_names()
