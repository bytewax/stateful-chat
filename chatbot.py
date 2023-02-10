import json
import os
import time

from bytewax.dataflow import Dataflow
from bytewax.execution import spawn_cluster
from bytewax.inputs import ManualInputConfig
from bytewax.outputs import ManualOutputConfig

import openai
import backoff

from pynats import NATSClient

NATS_URL = os.getenv("NATS_URL","nats://127.0.0.1:4222")
print(NATS_URL)
nats_client = NATSClient(url=NATS_URL)
print(nats_client._conn_options.hostname)
nats_client.connect()


OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
openai.api_key = os.environ.get('OPENAI_API_KEY')


def input_builder(worker_index, worker_count, state):
    # Ignore state recovery here
    state = None
    messages = []

    def callback(message):
        messages.append(message)

    nats_client.subscribe(subject="prompts", callback=callback)

    while True:
        nats_client.wait(count=1)
        yield None, messages.pop()

flow = Dataflow()
flow.input("input", ManualInputConfig(input_builder))


def key_on_user(msg):
    user_id = json.loads(msg.payload.decode())['user_id']
    return(user_id, msg)

flow.inspect(print)
flow.map(key_on_user)


@backoff.on_exception(backoff.expo, openai.error.RateLimitError)
def completions_with_backoff(**kwargs):
    return openai.Completion.create(**kwargs)


class Conversation:

    def __init__(self) -> None:
        self.session_responses = []
        self.session_prompts = []
        self.session_start = time.time()
        self.elapsed_time = 0

    def generate_response(self, msg):
        if len(self.session_responses) >= 1:
            chat_log = "\n".join([f"Human: {x[0]}\nAI:{x[1]}" for x in zip(self.session_prompts, self.session_responses)])
        else:
            chat_log = ""
        prompt = f"{chat_log}\nHuman: {msg.payload.decode()}\nAI:"
        response = completions_with_backoff(
            model="text-davinci-003",
            prompt=prompt,
            stop=['\nHuman'],
            temperature=0.6,
            max_tokens=2000
        )
        print(response)
        self.session_responses.append(response.choices[0].text)
        self.session_prompts.append(msg.payload.decode())
        return self, (msg, response.choices[0].text)

flow.stateful_map(
    step_id = "conversation",
    builder = lambda: Conversation(),
    mapper = Conversation.generate_response,
)
flow.inspect(print)


def output_builder(worker_index, worker_count):
    def publish(key__msg__response):
        key, (msg, response) = key__msg__response
        nats_client.publish(msg.reply, payload=response)
    
    return publish

flow.capture(ManualOutputConfig(output_builder))

if __name__ == "__main__":
    spawn_cluster(flow, proc_count = 1, worker_count_per_proc = 1,)
