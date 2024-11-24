FROM ollama/ollama:0.4.4

RUN apt update -y
RUN apt install python3 python3-pip -y

RUN ollama serve & \
    sleep 3s && \
    ollama pull llama3.2:1b

COPY requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /app
COPY app.py .
COPY llama.py .


EXPOSE 8501
ENTRYPOINT ["bash", "-c"]

# Command to start both services
CMD ["ollama serve & streamlit run app.py --server.port 8501"]