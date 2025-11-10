import os
import subprocess
import csv
import re
import json
import time
import sys
import platform
from datetime import timedelta
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4, MP4Tags
from pathlib import PureWindowsPath


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


CONFIG_FILE = resource_path("config.json")


def load_config():
    default = {
        "variants": [],
        "duration_min": 30,
        "duration_max": 600,
        "transcode_mp3": "false",
        "generate_m3u": "true",
        "exclude_instrumentals": "false",
    }
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                return {**default, **cfg}
        except:
            return default
    return default


def get_file_timestamps(file_path):
    return {
        "created": os.path.getctime(file_path),
        "modified": os.path.getmtime(file_path),
    }


def set_file_timestamps(file_path, timestamps):
    os.utime(file_path, (timestamps["modified"], timestamps["modified"]))


def embed_artwork(audio_file, jpg_file):
    print(f"\nEmbedding artwork for: {audio_file}")
    print(f"Using artwork: {jpg_file}")

    timestamps = get_file_timestamps(audio_file)

    audio_dir = os.path.dirname(audio_file)
    audio_filename = os.path.basename(audio_file)
    temp_output = os.path.join(audio_dir, f"temp_{audio_filename}")

    if platform.system() == "Darwin":
        ffmpeg_path = resource_path("ffmpeg")
        ffmpeg_exe = os.path.join(ffmpeg_path, "ffmpeg")
    elif platform.system() == "Linux":
        ffmpeg_exe = "ffmpeg"
    else:
        ffmpeg_path = resource_path("ffmpeg")
        ffmpeg_exe = os.path.join(
            ffmpeg_path, "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
        )

    cmd = [
        ffmpeg_exe,
        "-i",
        audio_file,
        "-i",
        jpg_file,
        "-map",
        "0:a",
        "-map",
        "1:v",
        "-c:a",
        "copy",
        "-c:v",
        "mjpeg",
        "-disposition:v:0",
        "attached_pic",
        temp_output,
    ]
    try:
        creationflags = (
            subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
        subprocess.run(
            cmd, check=True, capture_output=True, creationflags=creationflags
        )
        os.replace(temp_output, audio_file)
        set_file_timestamps(audio_file, timestamps)
        print(f"Successfully embedded artwork for {audio_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error processing {audio_file}: {e.stderr.decode()}")
        if os.path.exists(temp_output):
            os.remove(temp_output)


def clean_filename_for_artwork(filename):
    filename = os.path.splitext(filename)[0]
    return filename


def get_jpg_number(filename):
    match = re.match(r"^(\d+)_", filename)
    return int(match.group(1)) if match else float("inf")


def rename_album_art(output_dir, not_found_songs=None):
    if not_found_songs is None:
        not_found_songs = []

    failed_track_numbers = {song["Track Number"] for song in not_found_songs}

    audio_files = [
        f for f in os.listdir(output_dir) if f.lower().endswith((".mp3", ".m4a"))
    ]
    jpg_files = [f for f in os.listdir(output_dir) if f.endswith(".jpg")]

    audio_files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    jpg_files.sort(key=get_jpg_number)

    if len(audio_files) != len(jpg_files):
        print(
            f"Warning: Number of files doesn't match! Audio files: {len(audio_files)}, JPG: {len(jpg_files)}"
        )

    i = 0
    while i < len(audio_files) and i < len(jpg_files):
        audio_file = audio_files[i]
        jpg_file = jpg_files[i]

        jpg_number = get_jpg_number(jpg_file)

        if jpg_number in failed_track_numbers:
            jpg_files.pop(i)
            continue

        new_jpg_name = clean_filename_for_artwork(audio_file) + ".jpg"
        print(f"New JPG name: {new_jpg_name}")

        try:
            os.rename(
                os.path.join(output_dir, jpg_file),
                os.path.join(output_dir, new_jpg_name),
            )
            print(f"Successfully renamed {jpg_file} to {new_jpg_name}")
        except Exception as e:
            print(f"Error renaming file: {e}")

        i += 1


def embed_all_artwork(csv_path, output_dir, not_found_songs=None):
    if not_found_songs is None:
        not_found_songs = []

    print("\n=== Starting metadata and artwork embedding process ===")
    print(f"Number of not found songs: {len(not_found_songs)}")

    failed_track_numbers = {song["Track Number"] for song in not_found_songs}

    csv_data = []
    try:
        with open(csv_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            csv_data = [
                row for i, row in enumerate(reader, 1) if i not in failed_track_numbers
            ]
            print(
                f"\nLoaded {len(csv_data)} entries from CSV file (excluding failed tracks)"
            )
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return

    audio_files = [
        f for f in os.listdir(output_dir) if f.lower().endswith((".m4a", ".mp3"))
    ]
    jpg_files = [f for f in os.listdir(output_dir) if f.endswith(".jpg")]

    audio_files.sort(key=lambda x: os.path.getctime(os.path.join(output_dir, x)))

    csv_index = 0
    for audio_file in audio_files:
        print(f"\nProcessing audio file: {audio_file}")

        audio_base = os.path.splitext(audio_file)[0]
        matching_jpg = None
        for jpg_file in jpg_files:
            jpg_base = os.path.splitext(jpg_file)[0]
            if jpg_base == audio_base:
                matching_jpg = jpg_file
                break

        if matching_jpg:
            try:
                audio_path = os.path.join(output_dir, audio_file)
                jpg_path = os.path.join(output_dir, matching_jpg)

                if csv_index < len(csv_data):
                    row = csv_data[csv_index]
                    title = row.get("Track Name") or row.get("Track name") or "Unknown"
                    artist = (
                        row.get("Artist Name(s)") or row.get("Artist name") or "Unknown"
                    )
                    album = row.get("Album Name") or row.get("Album") or "Unknown"
                    csv_index += 1
                else:
                    title = os.path.splitext(audio_file)[0]
                    artist = "Unknown Artist"
                    album = "Unknown Album"

                if audio_file.lower().endswith(".m4a"):
                    audio = MP4(audio_path)
                    tags = audio.tags or MP4Tags()
                    tags["\xa9nam"] = [title]
                    tags["\xa9ART"] = [artist]
                    tags["\xa9alb"] = [album]
                    audio.save()
                else:  # MP3
                    try:
                        audio = EasyID3(audio_path)
                    except:
                        audio = EasyID3()
                    audio["title"] = title
                    audio["artist"] = artist
                    audio["album"] = album
                    audio.save()

                embed_artwork(audio_path, jpg_path)

            except Exception as e:
                print(f"Error processing {audio_file}: {str(e)}")


def normalize(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower())


def contains_keywords_in_order(candidate_title: str, keywords: list[str]) -> bool:
    txt = normalize(candidate_title)
    pos = 0
    for kw in keywords:
        idx = txt.find(kw, pos)
        if idx < 0:
            return False
        pos = idx + len(kw)
    return True


def convert_playlist(
    csv_path,
    output_folder,
    config,
    deep_search=True,
    transcode_mp3=False,
    generate_m3u=True,
    exclude_instrumentals=False,
    embed_thumbnails=False,
    spotify_art=False,
    progress_callback=None,
):
    """
    Core conversion function

    Args:
        csv_path: Path to CSV file with playlist
        output_folder: Folder to save downloaded files
        config: Configuration dictionary
        deep_search: Enable deep search mode
        transcode_mp3: Convert to MP3 format
        generate_m3u: Generate M3U playlist file
        exclude_instrumentals: Filter out instrumental versions
        embed_thumbnails: Embed video thumbnails as artwork
        spotify_art: Use Spotify album art
        progress_callback: Optional callback function(current, total, status_text)

    Returns:
        tuple: (downloaded_files, not_found_songs)
    """
    start_time = time.time()
    duration_min = config.get("duration_min", 0)
    duration_max = config.get("duration_max", float("inf"))

    playlist_name = os.path.splitext(os.path.basename(csv_path))[0]
    output_dir = os.path.join(output_folder, playlist_name)
    os.makedirs(output_dir, exist_ok=True)

    downloaded = []
    not_found_songs = []

    base_dir = os.path.dirname(os.path.abspath(__file__))
    if platform.system() == "Darwin":
        ffmpeg_exe = os.path.join(resource_path("ffmpeg"), "ffmpeg")
        yt_dlp_exe = os.path.join(resource_path("yt-dlp"), "yt-dlp")
    elif platform.system() == "Linux":
        ffmpeg_exe = "ffmpeg"
        yt_dlp_exe = "yt-dlp"
    else:
        ffmpeg_exe = os.path.join(base_dir, "ffmpeg", "ffmpeg.exe")
        yt_dlp_exe = os.path.join(base_dir, "yt-dlp", "yt-dlp.exe")

    rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
    total = len(rows)
    archive_file = os.path.join(output_dir, "downloaded.txt")
    creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

    for i, row in enumerate(rows, start=1):
        title = row.get("Track Name") or row.get("Track name") or "Unknown"
        artist_raw = row.get("Artist Name(s)") or row.get("Artist name") or "Unknown"
        artist_primary = re.split(r"[,/&]| feat\.| ft\.", artist_raw, flags=re.I)[
            0
        ].strip()
        safe_artist = re.sub(r"[^\w\s]", "", artist_primary)
        album = row.get("Album Name") or row.get("Album") or playlist_name
        spotify_ms = row.get("Duration (ms)")
        spotify_sec = (
            int(spotify_ms) / 1000 if spotify_ms and spotify_ms.isdigit() else None
        )

        safe_title = re.sub(r"[^\w\s]", "", title)
        variants = config.get("variants") or [""]
        if "instrumental" in title.lower():
            variants.insert(0, "instrumental")

        best_file = None
        for variant in variants:
            parts = [safe_title]
            if safe_artist and safe_artist.lower() != "unknown":
                parts.append(safe_artist)
            if variant:
                parts.append(variant)
            q = " ".join(parts)
            print(f"Searching for → {q!r}")

            if progress_callback:
                progress_callback(i, total, f"Searching: {q}")

            def yt_cmd(extra_args, search_spec):
                cmd = [
                    yt_dlp_exe,
                    f"--ffmpeg-location={os.path.dirname(ffmpeg_exe)}",
                    "--no-config",
                ]
                cmd += extra_args + [search_spec]
                return cmd

            if deep_search:
                # Deep search logic
                proc_q = subprocess.run(
                    yt_cmd(
                        ["--flat-playlist", "--dump-single-json", "--no-playlist"],
                        f"ytsearch1:{q}",
                    ),
                    capture_output=True,
                    text=True,
                    creationflags=creationflags,
                )
                try:
                    data_q = json.loads(proc_q.stdout) or {}
                except Exception:
                    data_q = {}
                if not isinstance(data_q, dict):
                    data_q = {}
                entries_q = (
                    data_q.get("entries")
                    if isinstance(data_q.get("entries"), list)
                    else []
                )
                top = entries_q[0] if entries_q else {}

                vid_title = top.get("title", "")
                upl = (top.get("uploader") or "").lower()
                duration = top.get("duration") or 0
                passes = (
                    safe_title.lower() in vid_title.lower()
                    and (not safe_artist or safe_artist.lower() in upl)
                    and (not spotify_sec or abs(duration - spotify_sec) <= 10)
                    and (duration >= duration_min and duration <= duration_max)
                )
                if passes:
                    download_spec = top.get(
                        "webpage_url",
                        f"https://www.youtube.com/watch?v={top.get('id','')}",
                    )
                else:
                    # Phase 2: deep search
                    proc_ids = subprocess.run(
                        yt_cmd(
                            ["--flat-playlist", "--dump-single-json", "--no-playlist"],
                            f"ytsearch3:{q}",
                        ),
                        capture_output=True,
                        text=True,
                        creationflags=creationflags,
                    )
                    try:
                        tmp = json.loads(proc_ids.stdout) or {}
                    except Exception:
                        tmp = {}
                    data_ids = tmp if isinstance(tmp, dict) else {}
                    entries_ids = (
                        data_ids.get("entries")
                        if isinstance(data_ids.get("entries"), list)
                        else []
                    )
                    ids = [e for e in entries_ids if isinstance(e, dict)][:3]

                    scored = []
                    first_words = normalize(title).split()[:5]
                    for entry in ids:
                        vid = entry.get("id")
                        url = f"https://www.youtube.com/watch?v={vid}"
                        proc_i = subprocess.run(
                            yt_cmd(["--dump-single-json", "--no-playlist"], url),
                            capture_output=True,
                            text=True,
                            creationflags=creationflags,
                        )
                        if "Sign in to confirm your age" in (proc_i.stderr or ""):
                            continue
                        try:
                            info = json.loads(proc_i.stdout) or {}
                        except Exception:
                            continue

                        raw_title = info.get("title", "")
                        low = raw_title.lower()
                        up2 = (info.get("uploader") or "").lower()
                        dur2 = info.get("duration") or 0

                        if dur2 < duration_min or dur2 > duration_max:
                            continue
                        if "shorts/" in info.get("webpage_url", "") or "#shorts" in low:
                            continue
                        if safe_artist.lower() and safe_artist.lower() not in up2:
                            continue
                        if variant and variant.lower() not in low:
                            continue
                        if not contains_keywords_in_order(raw_title, first_words):
                            continue

                        score = 100 if low.startswith(safe_title.lower()) else 80
                        if spotify_sec:
                            score -= abs(dur2 - spotify_sec)
                        scored.append((score, url))

                    download_spec = (
                        scored
                        and max(scored, key=lambda x: x[0])[1]
                        or f"ytsearch1:{q}"
                    )
            else:
                download_spec = f"ytsearch1:{q}"

            # Download
            file_title = re.sub(r"[^\w\s]", "", title).strip()
            base = f"{i:03d} - {file_title}" + (f" - {variant}" if variant else "")
            tmpl = base + ".%(ext)s"
            cmd_dl = yt_cmd(
                [
                    "--download-archive",
                    archive_file,
                    "-f",
                    "bestaudio[ext=m4a]/bestaudio",
                    "--output",
                    os.path.join(output_dir, tmpl),
                    "--no-playlist",
                ],
                download_spec,
            )

            if embed_thumbnails:
                cmd_dl += ["--embed-thumbnail", "--add-metadata"]
            if transcode_mp3:
                cmd_dl += [
                    "--extract-audio",
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    "0",
                ]
            else:
                cmd_dl += ["--remux-video", "m4a"]
            if exclude_instrumentals:
                cmd_dl += ["--reject-title", "instrumental"]

            ret = subprocess.run(
                cmd_dl, capture_output=True, text=True, creationflags=creationflags
            )
            if ret.returncode != 0:
                stderr = ret.stderr or ""
                if "Sign in to confirm your age" in stderr:
                    not_found_songs.append(
                        {
                            "Track Name": title,
                            "Artist Name(s)": artist_primary,
                            "Album Name": album,
                            "Track Number": i,
                            "Error": "Age-restricted video",
                        }
                    )
                    break
                else:
                    continue

            out_ext = ".mp3" if transcode_mp3 else ".m4a"
            candidate_path = os.path.join(output_dir, base + out_ext)
            if os.path.isfile(candidate_path):
                best_file = candidate_path
                if out_ext == ".m4a":
                    audio = MP4(best_file)
                    tags = audio.tags or MP4Tags()
                    tags["\xa9nam"] = [title]
                    tags["\xa9ART"] = [artist_primary]
                    tags["\xa9alb"] = [album]
                    audio.save()
                else:
                    audio = EasyID3()
                    try:
                        audio.load(best_file)
                    except:
                        pass
                    audio.update(
                        {
                            "artist": artist_primary,
                            "title": title,
                            "album": album,
                            "tracknumber": str(i),
                        }
                    )
                    audio.save()
                downloaded.append(os.path.basename(best_file))
                break

        if not best_file:
            not_found_songs.append(
                {
                    "Track Name": title,
                    "Artist Name(s)": artist_primary,
                    "Album Name": album,
                    "Track Number": i,
                    "Error": "No valid download",
                }
            )

        elapsed = time.time() - start_time
        eta = timedelta(seconds=int((elapsed / i) * (total - i)))

        if progress_callback:
            progress_callback(i, total, f"Downloaded {i}/{total}, ETA: {eta}")

    # Save not found songs
    if not_found_songs:
        nf_path = os.path.join(output_dir, f"{playlist_name}_not_found.csv")
        with open(nf_path, "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(
                cf,
                fieldnames=[
                    "Track Name",
                    "Artist Name(s)",
                    "Album Name",
                    "Track Number",
                    "Error",
                ],
            )
            writer.writeheader()
            writer.writerows(not_found_songs)

    # Generate M3U playlist
    if generate_m3u:
        m3u_filename = playlist_name.replace("_", " ")
        m3u_path = os.path.join(output_dir, f"{m3u_filename}.m3u")
        with open(m3u_path, "w", encoding="utf-8") as m3u:
            m3u.write("#EXTM3U\n")
            audio_files = sorted(
                [
                    f
                    for f in os.listdir(output_dir)
                    if f.lower().endswith((".mp3", ".m4a"))
                ],
                key=lambda x: os.path.getctime(os.path.join(output_dir, x)),
            )
            for fn in audio_files:
                m3u.write(f"#EXTINF:-1,{os.path.splitext(fn)[0]}\n")
                m3u.write(f"{fn}\n")

    # Handle Spotify artwork
    if spotify_art:
        rename_album_art(output_dir, not_found_songs)
        embed_all_artwork(csv_path, output_dir, not_found_songs)

    print(f"✅ Completed in {timedelta(seconds=int(time.time()-start_time))}")

    return downloaded, not_found_songs
