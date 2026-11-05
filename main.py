import math
import subprocess
import tempfile
import time
from pathlib import Path

import torch
from torchcodec.decoders import VideoDecoder
from torchcodec.encoders import VideoEncoder
import static_ffmpeg

ffmpeg, ffprobe = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()

print("FFmpeg:", ffmpeg)
def stacktofile(encoded_tensors, out_path, chunk=16, device="cuda", fps=None):
    decoders = [VideoDecoder(t, device=device) for t in encoded_tensors]

    n_frames = min(len(d) for d in decoders)
    W = decoders[0].metadata.width
    H = sum(d.metadata.height for d in decoders)
    if fps is None:
        fps = decoders[0].metadata.average_fps

    cmd = [
        ffmpeg, "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(fps),
        "-i", "pipe:0",
        "-threads", "4",
        #"-crf", "0",
        "-c:v", "h264_nvenc", "-preset", "p7",
        "-pix_fmt", "yuv420p",
        out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)  # stderr inherited -> no pipe deadlock

    try:
        for start in range(0, n_frames, chunk):
            stop = min(start + chunk, n_frames)
            parts = [d.get_frames_in_range(start, stop).data for d in decoders]  # each (t, C, h, w)
            stacked = torch.cat(parts, dim=2)                 # stack along height -> (t, C, H, W)
            frames = stacked.permute(0, 2, 3, 1).cpu()  # (t, H, W, C) for rgb24
            proc.stdin.write(frames.numpy())
            del parts, stacked, frames
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
    except BaseException:
        proc.kill()
        raise





def applyFTT(input_path, output_path):

    DEVICE = torch.device("cuda")
    total_gpu_memory = torch.cuda.get_device_properties(DEVICE).total_memory
    print("Opening video...")
    decoder = VideoDecoder(input_path)
    frame_count = len(decoder)
    print("Metadata:", decoder.metadata)
    fps = decoder.metadata.average_fps
    print(f"Frame Rate: {fps}")
    first_frame = decoder.get_frame_at(0).data

    if first_frame.ndim != 3:
        raise RuntimeError(
            f"Unexpected frame shape: "
            f"{first_frame.shape}"
        )

    channels, video_height, video_width = (
        first_frame.shape
    )

    print(
        "Resolution:",
        f"{video_width}x{video_height}"
    )

    print(
        "Channels:",
        channels
    )

    print("Finding GPU tile size...")
    pixels = math.floor((total_gpu_memory) / (channels * 4 * 2 * frame_count))

    print(pixels)
    pixels = math.floor((pixels / video_width) / 3) * video_width
    pixels = (pixels // video_width // 2) * 2 * video_width
    print(f'Wanting to do {pixels / video_width}')
    pixels = min(max(pixels, video_width * 64),video_width*video_height)
    print(f'Doing do {pixels / video_width}')
    h=(int)(pixels / video_width)
    print(pixels)
    stacksize = math.ceil((video_width * video_height / pixels))

    a=time.time()
    az=time.time()

    splitinto = stacksize
    crops = []
    maps = []
    print("Cropping Videos")
    for i in range(splitinto):
        crops.append(f"[0:v]crop={video_width}:{(int)(video_height-(splitinto-1)*h) if i==splitinto-1 else h}:0:{(h*i)}[v{i}]")
    for i in range(splitinto):
        maps.append( "-map")
        maps.append(f"[v{i}]")
    cmd = [
        ffmpeg, "-v", "error",
        "-i", input_path,
        "-filter_complex",
        ";".join(crops),
        *maps,
        "-c:v", "libx264",
        "-threads", "4",
        "-preset", "ultrafast",
        #"-crf", "0",
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "frag_keyframe+empty_moov",
        "-f", "mp4",
        "pipe:1",
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )

    mp4_bytes = result.stdout







    print(f"Encoded size: {len(mp4_bytes) / 1024**2:.2f} MiB")
    encoded_tensors=[]
    print("Starting processing...")

    for i in range(splitinto):
        b = time.time()
        decoder = VideoDecoder(mp4_bytes, stream_index=i, device="cuda", ) #-57.19824552536011
        print(f"Decoder {b - time.time()}")
        b = time.time()
        video = decoder[:].to(DEVICE, dtype=torch.float32)  # (T, C, H, W)
        print(f"Decoding {b - time.time()}")
        b = time.time()
        video = torch.fft.rfft(video, dim=0)
        video = torch.abs(video)
        video = torch.fft.irfft(video, dim=0, n=frame_count)

        #video = torch.abs(video)
        video = torch.floor(video%256).to(torch.uint8)
        video = video.clamp(0, 255).to(torch.uint8)
        print(f"Process {b - time.time()}")
        b = time.time()

        #Process the video

        #print(f"Crop tensor shape: {tuple(video.shape)}")
        #print(f"Crop size: {video.shape[-1]} x {video.shape[-2]} pixels")
        #print(len(video))
        #print(i)
        # Encode the tensor to an MP4 using TorchCodec.
        #video = video.cpu()
        encoder = VideoEncoder(
            video,
            frame_rate=fps,
        )
        print(f"Encoder {b - time.time()}")
        b = time.time()
        encoded_tensors.append( encoder.to_tensor(
            format="mp4",
            codec="h264_nvenc",
            #crf=0,
            preset="p7",
        ))
        print(f"Save {b - time.time()}")
        b = time.time()
        print(sum(t.untyped_storage().nbytes() for t in encoded_tensors) / 2 ** 20, "MiB held",i)


    print(az-time.time())
    print("Writing to file...")
    stacktofile(encoded_tensors, output_path)
    print(a-time.time())

applyFTT("input.mp4","output.mp4")