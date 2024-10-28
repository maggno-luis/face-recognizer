import os
import uuid
import pickle
import datetime
import time
import shutil
import cv2
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import face_recognition
import starlette.responses
import serial

# Defina os diretórios onde as imagens e logs serão armazenados
ATTENDANCE_LOG_DIR = '/home/magno/projeto-iot/db/logs'
DB_PATH = '/home/magno/projeto-iot/db/images'
for dir_ in [ATTENDANCE_LOG_DIR, DB_PATH]:
    if not os.path.exists(dir_):
        os.makedirs(dir_)
''
app = FastAPI()

# Configuração do CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#arduino = serial.Serial(port='COM4', baudrate=9600)
# Função que envia informações para o arduino

"""
def send_to_arduino(message):
    arduino.write(bytes(message, 'utf-8'))
"""

# Função de reconhecimento facial
def recognize(img):
    embeddings_unknown = face_recognition.face_encodings(img)
    if len(embeddings_unknown) == 0:
        return 'no_persons_found', False
    else:
        embeddings_unknown = embeddings_unknown[0]

    match = False
    j = 0
    db_dir = sorted([j for j in os.listdir(DB_PATH) if j.endswith('.pickle')])
    while not match and j < len(db_dir):
        path_ = os.path.join(DB_PATH, db_dir[j])
        with open(path_, 'rb') as file:
            embeddings = pickle.load(file)[0]
        match = face_recognition.compare_faces([embeddings], embeddings_unknown)[0]
        j += 1

    if match:
        return db_dir[j - 1][:-7], True
    else:
        return 'unknown_person', False

# Rota de login
@app.post("/login")
async def login(file: UploadFile = File(...)):
    file_path = os.path.join("/tmp", f"{uuid.uuid4()}.png")
    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    user_name, match_status = recognize(cv2.imread(file_path))

    if match_status:
        date = datetime.datetime.now().strftime('%Y%m%d')
        log_path = os.path.join(ATTENDANCE_LOG_DIR, f'{date}.csv')
        with open(log_path, 'a') as f:
            f.write(f'{user_name},{datetime.datetime.now()},IN\n')
    #     send_to_arduino('verde')

    #else:
    #    send_to_arduino('vermelho')

    os.remove(file_path)
    return {'user': user_name, 'match_status': match_status}

# Rotapoint de logout
@app.post("/logout")
async def logout(file: UploadFile = File(...)):
    file_path = os.path.join("/tmp", f"{uuid.uuid4()}.png")
    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    user_name, match_status = recognize(cv2.imread(file_path))

    if match_status:
        date = datetime.datetime.now().strftime('%Y%m%d')
        log_path = os.path.join(ATTENDANCE_LOG_DIR, f'{date}.csv')
        with open(log_path, 'a') as f:
            f.write(f'{user_name},{datetime.datetime.now()},OUT\n')

    os.remove(file_path)
    return {'user': user_name, 'match_status': match_status}

# Rota para registrar um novo usuário
@app.post("/register_new_user")
async def register_new_user(file: UploadFile = File(...), text: str = None):
    file_path = os.path.join("/tmp", f"{uuid.uuid4()}.png")
    contents = await file.read()

    with open(file_path, "wb") as f:
        f.write(contents)

    shutil.copy(file_path, os.path.join(DB_PATH, f'{text}.png'))
    embeddings = face_recognition.face_encodings(cv2.imread(file_path))
    
    with open(os.path.join(DB_PATH, f'{text}.pickle'), 'wb') as file_:
        pickle.dump(embeddings, file_)

    os.remove(file_path)
    return {'registration_status': 200}

# Rota para obter os logs de presença
@app.get("/get_attendance_logs")
async def get_attendance_logs():
    zip_filename = 'attendance_logs.zip'
    shutil.make_archive(zip_filename[:-4], 'zip', ATTENDANCE_LOG_DIR)
    return starlette.responses.FileResponse(zip_filename, media_type='application/zip', filename=zip_filename)
