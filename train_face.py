import cv2
import os
import numpy as np

def train_admin_face():
    # Load OpenCV's built-in face detector (Haar Cascade)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Initialize LBPH Face Recognizer
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    faces = []
    ids = []
    
    base_path = "admin_faces"
    if not os.path.exists(base_path):
        print(f"Directory {base_path} not found.")
        return

    # Process images in the directory
    image_paths = [os.path.join(base_path, f) for f in os.listdir(base_path) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    if not image_paths:
        print("No images found in admin_faces directory. Please add 10 images of the admin.")
        return

    print(f"Found {len(image_paths)} images. Processing...")

    for image_path in image_paths:
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Improve contrast for better detection/recognition
        gray = cv2.equalizeHist(gray)
        
        # Detect faces in the image
        detected_faces = face_cascade.detectMultiScale(gray, 1.1, 6)
        
        for (x, y, w, h) in detected_faces:
            face_roi = gray[y:y+h, x:x+w]
            faces.append(face_roi)
            ids.append(1) # ID 1 for Admin
            print(f"  - Face captured from {os.path.basename(image_path)}")
            
    if faces:
        recognizer.train(faces, np.array(ids))
        # Save the model
        recognizer.save("admin_face_model.yml")
        print("Model trained and saved as admin_face_model.yml")
    else:
        print("No faces detected in the provided images.")

if __name__ == "__main__":
    train_admin_face()
