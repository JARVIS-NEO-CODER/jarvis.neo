import cv2

print("Tentative d'ouverture de la caméra...")

# On force l'API DirectShow (essentiel sous Windows pour forcer l'alerte/l'accès)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Erreur : Impossible d'ouvrir la caméra avec DirectShow. Essai standard...")
    cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Échec critique : La caméra est inaccessible.")
else:
    print("Caméra ouverte avec succès ! Appuyez sur 'q' dans la fenêtre vidéo pour fermer.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur de lecture du flux.")
            break
        
        cv2.imshow("Test Camera JARVIS", frame)
        
        # Quitter avec la touche 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Test terminé proprement.")