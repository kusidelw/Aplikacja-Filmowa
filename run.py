from app import create_app

app = create_app()

if __name__ == "__main__":
    # debug=True sprawia, że serwer sam się restartuje po zapisaniu zmian w kodzie
    app.run(debug=True)
