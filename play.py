import ffmpeg
import numpy as np
from subprocess import TimeoutExpired

def read_audio_from_rtsp(rtsp_url, output_file):
    process = (
        ffmpeg
        .input(rtsp_url)
        .output(output_file, format='wav', acodec='pcm_s16le', ac=2, ar='44100', b='192k', bufsize='1920k')
        .overwrite_output()
        .run_async(pipe_stderr=True)
    )
    
    try:
        while True:
            try:
                process.wait(timeout=1)
                break
            except TimeoutExpired:
                print("Enregistrement en cours...")
                continue
            except KeyboardInterrupt:
                process.terminate()
                break
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        process.terminate()
        process.wait()

    print(f"Audio saved to {output_file}")

# Exemple d'utilisation
rtsp_url = "rtsp://localhost:8554/mic"
output_file = "recorded_audio.wav"

read_audio_from_rtsp(rtsp_url, output_file)

