# tests.dataset_generator

from ragas.testset import TestsetGenerator
from ragas.llms import llm_factory
from ragas.embeddings.openai_provider import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from openai import OpenAI
from src.pyxon.storage.vs import VectorStore
from src.config import Settings

client = OpenAI(api_key=Settings.OPENAI_API_KEY)
_vs = VectorStore()
llm = llm_factory(Settings.TEST_MODEL, client=client)
embedding_func = OpenAIEmbeddings(client, Settings.EMBEDDING_MODEL_NAME)

testset_generator = TestsetGenerator(llm, embedding_func)
docs = _vs.get_all_chunks()

testset = testset_generator.generate_with_langchain_docs(docs, testset_size=Settings.TESTSET_SIZE)

testset.to_csv(Settings.TESTSET)