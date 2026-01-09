from fastapi import FastAPI, Form, UploadFile, File
from pydantic import BaseModel, field_validator, EmailStr, conint
from typing import List

PositiveInt = conint(gt=0)

app = FastAPI()


class user(BaseModel):
    user_id: int
    name: str
    email: EmailStr

    @field_validator("user_id")
    def validate_user_id(cls, value):
        if value <= 0:
            raise ValueError("user_id must be a positive integer")
        return value


@app.post("/login/")
async def login(username: str = Form(...), password: str = Form(...)):
    return {"username": username, "password": "********"}


@app.post("/uploadFile/")
async def create_upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename, "content_type": file.content_type}


@app.post("/saveFile/")
async def save_upload_file(file: UploadFile = File(...)):
    with open(f'uploads/{file.filename}', "wb") as f:
        f.write(file.file.read())
    return {"message": f"File '{file.filename}' saved successfully"}


@app.post("/uploadMultipleFiles/")
async def create_upload_files(files: List[UploadFile] = File(...)):
    return {"filenames": [file.filename for file in files]}


@app.post("/users/")
async def create_user(user: user):
    # u = {"user_id": user.user_id, "name": user.name, "email": user.email}
    return user


@app.get("/users/{user_id}")
async def read_user(user: user):
    # In a real application, you would retrieve the user from a database
    return {"name": user.name, "email": user.email}

# @app.get("/")
# def read_root():
#     return {"message": "Welcome to FastAPI"}


# @app.post("/items/")
# def create_item(name: str, price: float):
#     return {"name": name, "price": price}


# @app.put("/items/{item_id}")
# def update_item(item_id, name, price):
#     return {"item_id": item_id, "name": name, "price": price}


# @app.delete("/items/{item_id}")
# def delete_item(item_id: int):
#     return {"message": f"Item {item_id} deleted"}


# @app.get("/users/")
# def road_user(user_id: int, name: str):
#     return {"user_id": user_id, "name": name}


# @app.get("/users/{user_id}/details")
# def read_user_details(user_id: int, include_email: bool = False):
#     if include_email:
#         return {"user_id": user_id, "email": "email included"}
#     else:
#         return {"user_id": user_id, "email": "email not included"}
