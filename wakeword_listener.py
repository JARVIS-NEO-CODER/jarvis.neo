import whisper
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os

# Chargement du modèle Whisper au démarrage (ex: "base" ou "small" pour un bon compromis vitesse/précision)
print("[Système Whisper] Chargement du modèle local...")
whisper_model = whisper.load_model("base")
print("[Système Whisper] Modèle chargé avec succès.")

def ecouter_et_transcrire_whisper(duree_sec=5, fs=16000):
    """
    Enregistre l'audio du micro pendant un temps donné et le transcrit localement via Whisper.
    """
    print("[Whisper] Enregistrement en cours...")
    # Enregistrement audio via sounddevice
    audio = sd.rec(int(duree_sec * fs), samplerate=fs, channels=1, dtype=np.int16)
    sd.wait()  # Attend la fin de l'enregistrement
    print("[Whisper] Traitement et transcription...")

    # Sauvegarde temporaire dans un fichier wav
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav.close()
    
    wav.write(temp_wav.name, fs, audio)

    try:
        # Transcription locale par Whisper
        result = whisper_model.transcribe(temp_wav.name, language="fr")
        texte_transcrit = result["text"].strip()
        return texte_transcrit
    except Exception as e:
        print(f"[Erreur Whisper] : {e}")
        return ""
    finally:
        if os.path.exists(temp_wav.name):
            try:
                os.remove(temp_wav.name)
            except:
                pass