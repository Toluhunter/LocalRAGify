import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import OllamaLLM, OllamaEmbeddings

from langchain.docstore.document import Document
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.chains.history_aware_retriever import create_history_aware_retriever

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.graph.state import START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import Annotated, Sequence, TypedDict


class State(TypedDict):
    input: str
    chat_history: Annotated[Sequence[BaseMessage], add_messages]
    context: str
    answer: str

class LocalRagAgent:
    def __init__(self, model="llama3.2:1b"):

        # Initialize the model
        self.model = OllamaLLM(model=model)
        
        self.vector_store = self.__setup_vectorstore()
        retriever = self.vector_store.as_retriever(search_kwargs={"k":3, "fetch_k": 5})
        self.context_retriever = self.__contextualize_question(self.model, retriever)

        system_prompt = (
        "You are an intelligent assistant. You can follow basic instructions,"
        "answer casual greetings, and use retrieved context when needed. "
        "Prioritize responding naturally to direct instructions or greetings, "
        "and only use context when it enhances the response."
        "\n\n"
        "\n\n"
        "<Context>"
        "{context}"
        "\n\n"
        "</Context>"
        )

        # Define the prompt template
        self.prompt_message = [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("user", "{input}"),
        ]
        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages(self.prompt_message)


        # Chain the model and prompt together
        qa_chain = self.prompt | self.model
        self.chain = create_retrieval_chain(self.context_retriever, qa_chain)
        workflow = StateGraph(state_schema=State)
        workflow.add_edge(START, "model")
        workflow.add_node("model", self.__call_model)

        self.memory = MemorySaver()
        self.app = workflow.compile(checkpointer=self.memory)
        self.config = {"configurable": {"thread_id": "LOCALRAG11"}}

    def __contextualize_question(self, model, retriever):
        '''Contextualize the question with the vector store'''
        ### Contextualize question ###
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user input "
            "which might reference context in the chat history, "
            "formulate a standalone input which can be understood "
            "without the chat history. Do NOT respond to the input, "
            "just reformulate it if needed and otherwise return it as is."
        )
        contextualize_q_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        history_aware_retriever = create_history_aware_retriever(
            model, retriever, contextualize_q_prompt
        )
        return history_aware_retriever
    
    def __setup_vectorstore(self, model="llama3.2:1b"):
        '''Setup the vector store with empty index'''
        index_name = "local-rag"
        docsearch = OpenSearchVectorSearch(
            opensearch_url="https://vectorestore:9200",
            http_auth=("admin", "admin"),
            embedding_function=OllamaEmbeddings(model=model),
            index_name=index_name,
            use_ssl = False,
            verify_certs = False,
            ssl_assert_hostname = False,
            ssl_show_warn = False
        )
        if not docsearch.index_exists():
            docsearch.add_documents([Document(page_content="", metadata={"source": "init"})])
       
        return docsearch
    
    def update_knowledge(self, file_path):
        '''Update the knowledge base with a file'''
        text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=450, chunk_overlap=0, separators=["\n\n", "\n", " ", ""]
        )
        documents = PyPDFLoader(file_path).load_and_split(text_splitter)
        self.vector_store.add_documents(documents)
    

    def __call_model(self, state: State):
        response = self.chain.invoke(state)
        return {
            "chat_history": [
                HumanMessage(state["input"]),
                AIMessage(response["answer"]),
            ],
            "context": response["context"],
            "answer": response["answer"],
        }
    
    def invoke(self, question):
        '''Invoke the model with a question'''

        result = self.app.invoke(
            {"input": question},
            config=self.config,
        )
        return result["answer"]



if __name__ == "__main__":
    
    model_prompt = LocalRagAgent()
    try:
        while question := input("Question: "):
            answer = model_prompt.invoke(question)
            print(answer)
    except KeyboardInterrupt:
        print("\nGoodbye!")