import uvicorn

if __name__ == "__main__":
    print("Open http://127.0.0.1:8000 in your browser.")
    uvicorn.run("cornerbrief.app:app", host="127.0.0.1", port=8000)
