import streamlit as st
from pynats import NATSClient

import json
import os
import time


base_uri = "http://localhost:8082"

# set up page details
st.set_page_config(
    page_title="Bytewax ChatGPT",
    page_icon="🐝",
    layout="wide",
)

st.title("Bytewax ChatGPT")

if __name__ == "__main__":
    
    user_id = st.text_input('Enter your user id')
    print(user_id)
    prompt = st.text_input('Enter your question here')
    if st.button("Submit"):
        print("querying for {prompt}")
        with NATSClient() as client:
            payload = json.dumps({
                    "user_id":user_id,
                    "prompt":prompt})
            print(payload)
            msg = client.request("prompts", payload=payload.encode())
        st.write(msg.payload.decode())