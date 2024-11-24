import streamlit as st #all streamlit commands will be available through the "st" alias
from llama import LocalRagAgent #import the LocalRagAgent class from the llama.py file
import os

st.set_page_config(page_title="Chatbot") #HTML title
st.title("RAG Chatbot") #page title

if 'chat_history' not in st.session_state: #see if the chat history hasn't been created yet
    st.session_state.chat_history = [] #initialize the chat history

if 'agent' not in st.session_state: #see if the agent hasn't been created yet
    st.session_state.agent = LocalRagAgent() #initialize the agent

uploaded_file = st.sidebar.file_uploader("Choose a file", type=['pdf'])

rag_button = st.sidebar.button("Update Knowledge Base")

if rag_button:
    temp_file = f"./temp-{uploaded_file.name}.pdf"
    with open(temp_file, "wb") as file:
        file.write(uploaded_file.getvalue())
    
    try:
        st.session_state.agent.update_knowledge(temp_file)
        st.success(f"Knowledge base updated with {uploaded_file.name}")
        os.remove(temp_file)

    except Exception as e:
        st.error(e)



#Re-render the chat history (Streamlit re-runs this script, so need this to preserve previous chat messages)
for message in st.session_state.chat_history: #loop through the chat history
    with st.chat_message(message["role"]): #renders a chat line for the given role, containing everything in the with block
        if message["type"] == "text":
            st.markdown(message["data"]) #display the chat content
        
        elif message["type"] == "image":
            st.image(message["data"])



input_text = st.chat_input("Chat with your bot here") #display a chat input box


if input_text: #run the code in this if block after the user submits a chat message
    
    with st.chat_message("user"): #display a user chat message
        st.markdown(input_text) #renders the user's latest message
    
    st.session_state.chat_history.append({"role":"user", "data":input_text, "type": "text"}) #append the user's latest message to the chat history
    
    output = st.session_state.agent.invoke(input_text) #set the output to the user's message For now

    with st.chat_message("assistant"): #display a bot chat message
        st.markdown(output) #display bot's latest response

    st.session_state.chat_history.append({"role":"assistant", "data":output, "type": "text"}) #append the bot's latest message to the chat history
    