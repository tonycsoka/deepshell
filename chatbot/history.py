import os
import aiofiles
import numpy as np
from ollama import embeddings
from utils.logger import Logger
from config.settings import EMBEDDING_MODEL
from sklearn.metrics.pairwise import cosine_similarity

logger = Logger.get_logger()

class HistoryManager:
    def __init__(self, top_k=2, similarity_threshold=0.5):
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.history = []
        self.history_embeddings = []
        self.file_embeddings = {}
        self.folder_structure = {}
        self.char_limit = 10000

        logger.info("HistoryManager initialized.")

    ## === CONVERSATION HISTORY === ##

    async def add_message(self, role, message):
        """Stores raw messages and their embeddings."""
        logger.debug(f"Adding message: {message}")
        self.history.append({"role": role, "message": message})
        embedding = await self._fetch_embedding(message)  # Async fetch
        self.history_embeddings.append(embedding)
        logger.debug(f"Message added. Current history size: {len(self.history)}")

    async def get_relevant_context(self, query):
        """Finds relevant past messages using cosine similarity."""
        logger.debug(f"Fetching relevant context for query: {query}")

        if not self.history_embeddings and not self.folder_structure:
            logger.info("No history or folder structure available. Returning query as-is.")
            return query  # Return query if no history exists
        
        context = ""
        
        # If history is available, fetch relevant messages
        if self.history_embeddings:
            query_embedding = await self._fetch_embedding(query)
            similarities = cosine_similarity([query_embedding], self.history_embeddings)[0]
            top_indices = np.argsort(similarities)[-self.top_k:][::-1]

            relevant_messages = [
                self.history[i]["message"]
                for i in top_indices if similarities[i] >= self.similarity_threshold
            ]
            context += "\n".join(relevant_messages) if relevant_messages else ""
        
        # If folder structure is available, fetch relevant folder content
        if self.folder_structure:
            context += f"\nFolder Structure:\n{self.folder_structure}"

        # If neither context nor relevant files, return query as-is
        if not context.strip():
            logger.info("No relevant context or files. Returning query as-is.")
            return query
        
        return context

    ## === FILE HANDLING === ##

    async def add_file(self, file_path, content):
        """Embeds file content and stores reference."""
        logger.debug(f"Adding file: {file_path}")
        embedding = await self._fetch_embedding(content)
        self.file_embeddings[file_path] = embedding  # Store embedding linked to file path
        logger.info(f"Embeddings stored for file: {file_path}")
        logger.debug(f"Total number of files stored: {len(self.file_embeddings)}")

     
    async def get_relevant_files(self, query, top_k=1):
        """Retrieves most relevant files and ensures explicitly mentioned files are included."""
        logger.debug(f"Fetching relevant files for query: {query}")

        if not self.file_embeddings:
            logger.info("No files stored. Checking direct file match.")
            return await self._fetch_explicit_files(query)

        query_embedding = await self._fetch_embedding(query)
        file_paths = list(self.file_embeddings.keys())
        file_embeddings = list(self.file_embeddings.values())

        similarities = cosine_similarity([query_embedding], file_embeddings)[0]
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        relevant_files = await self._fetch_explicit_files(query)  # Ensure explicitly mentioned files are included
        for i in top_indices:
            if similarities[i] >= self.similarity_threshold:
                file_path = file_paths[i]
                if file_path not in [f[0] for f in relevant_files]:  # Avoid duplicate files
                    try:
                        async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                            content = await file.read()
                        relevant_files.append((file_path, content))
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")

        logger.debug(f"Relevant files found: {len(relevant_files)}")
        return relevant_files

    async def _fetch_explicit_files(self, query):
        """Fetches files explicitly mentioned in the query."""
        mentioned_files = []
        for file_path in self.file_embeddings.keys():
            if os.path.basename(file_path) in query:
                try:
                    async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                        content = await file.read()
                    mentioned_files.append((file_path, content))
                except Exception as e:
                    logger.error(f"Error reading explicitly mentioned file {file_path}: {str(e)}")

        return mentioned_files

    async def generate_prompt(self, query):
        """Retrieves context from history and files, then builds the final prompt."""
        logger.debug(f"Generating prompt for query: {query}")

        context = await self.get_relevant_context(query)
        relevant_files = await self.get_relevant_files(query)

        file_references = ""
        for file_path, content in relevant_files:
            file_references += f"\n[Referenced File: {file_path}]\n{content[:self.char_limit]}\n..."  # Limit file content to 10000 chars

        # Only include Context and Files if relevant data exists
        if context or file_references:
            prompt = f"Context:\n{context}\n\nUser Query: {query}\n\n{file_references}"
        else:
            prompt = query

        logger.debug(f"Generated prompt: {prompt}")
        return prompt


    ## === FOLDER STRUCTURE HANDLING === ##

    def add_folder_structure(self, structure):
        """
        Generates folder structure and appends it to the class's storage.
        """
        self.folder_structure = structure  # Store the structure for future use


    ## === HELPERS === ##

    async def _fetch_embedding(self, text):
        """Fetches embedding using the 'nomic-embed-text' model."""
        try:
            response = embeddings(model=EMBEDDING_MODEL, prompt=text)
            embedding = response['embedding']
            return embedding
        except Exception as e:
            logger.error(f"Error fetching embedding for message: {text}. Error: {str(e)}")
            return []


