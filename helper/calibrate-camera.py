import cv2
import time
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Camera calibration tool')
parser.add_argument('--index', type=int, default=0, help='Camera index (default: 0)')
parser.add_argument('--fps', type=int, default=10, help='Frame rate (default: 10, max: 60)')
args = parser.parse_args()

# Validate FPS
MAX_FPS = 70
if args.fps > MAX_FPS:
    print(f"Warning: FPS {args.fps} exceeds maximum of {MAX_FPS}. Setting to {MAX_FPS}.")
    args.fps = MAX_FPS
if args.fps < 1:
    print(f"Warning: FPS {args.fps} is too low. Setting to 1.")
    args.fps = 1

# Open camera
cap = cv2.VideoCapture(args.index)

# Try lower resolution first
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, args.fps)

# Wait a bit for camera to initialize
time.sleep(2)

print(f"Camera {args.index} connected at {args.fps} fps. Press 'q' to quit.")

try:
    frame_count = 0
    while True:
        # Read frame
        ret, frame = cap.read()
        
        if not ret:
            frame_count += 1
            if frame_count > 10:
                print(f"Failed to grab frame after {frame_count} attempts")
                break
            time.sleep(0.1)
            continue
        
        # Reset counter on success
        frame_count = 0
        
        # Display the frame
        cv2.imshow(f'Camera {args.index} ({args.fps} fps) - Press Q to quit', frame)
        
        # Break loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
except KeyboardInterrupt:
    print("\nStopped by user")
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Camera disconnected.")