# build docker image
docker build . -t bytewax-chatbot 

# run dataflow
docker compose up -e OPENAI_API_KEY=`$OPENAI_API_KEY`