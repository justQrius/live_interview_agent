import pyaudiowpatch as pyaudio

def list_devices():
    p = pyaudio.PyAudio()
    print("\n=== Audio Devices Found ===")
    
    wasapi_info = None
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_loopback = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        print(f"\nDefault System Output (What we try to capture):")
        print(f"  ID: {default_loopback['index']}")
        print(f"  Name: {default_loopback['name']}")
    except Exception as e:
        print(f"Could not determine default WASAPI device: {e}")

    if wasapi_info:
        print("\nAll WASAPI Input Devices (Loopback candidates):")
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev["hostApi"] == wasapi_info["index"] and dev["maxInputChannels"] > 0:
                print(f"  ID: {dev['index']} - Name: {dev['name']}")
                if dev["isLoopbackDevice"]:
                     print(f"    [Loopback] This is a valid capture target")

    p.terminate()

if __name__ == "__main__":
    list_devices()
