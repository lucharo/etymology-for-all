from fastapi import FastAPI, HTTPException
from .database import fetch_etymology, fetch_random_word

app = FastAPI()

@app.get('/graph/{word}')
def get_graph(word: str):
    graph = fetch_etymology(word)
    if not graph:
        raise HTTPException(status_code=404, detail='Word not found')
    return graph

@app.get('/random')
def random_word():
    return fetch_random_word()
