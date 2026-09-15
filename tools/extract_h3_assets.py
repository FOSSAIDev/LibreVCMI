#!/usr/bin/env python3
"""
LibreVCMI Asset Extractor
Extracts and converts all assets from Heroes of Might and Magic III data files (.lod, .snd, .vid)
into modern standard formats (PNG, WAV, TXT, SMK/BIK) with a full JSON manifest for LibreVCMI development.
"""

import os
import sys
import struct
import zlib
import json
import argparse
from pathlib import Path
from PIL import Image

def parse_h3_pcx(data):
    """
    Parses Heroes 3 PCX format and returns a PIL Image or None.
    H3 PCX header:
      uint32 size (width * height or width * height * 3)
      uint32 width
      uint32 height
    """
    if len(data) < 12:
        return None
    fsize, width, height = struct.unpack("<III", data[:12])
    if width == 0 or height == 0 or width > 8192 or height > 8192:
        return None

    expected_24b = width * height * 3
    expected_8b = width * height

    # 24-bit RGB
    if fsize == expected_24b and len(data) >= 12 + fsize:
        return Image.frombytes("RGB", (width, height), data[12:12+fsize])

    # 8-bit Indexed with 768-byte palette at end
    if fsize == expected_8b and len(data) >= 12 + fsize + 768:
        pixels = data[12:12+fsize]
        palette = data[12+fsize:12+fsize+768]
        img = Image.frombytes("P", (width, height), pixels)
        img.putpalette(palette)
        return img

    # Fallback for some variants where palette is placed differently or 8-bit without embedded palette
    if len(data) >= 12 + width * height:
        pixels = data[12:12+width*height]
        img = Image.frombytes("L", (width, height), pixels)
        return img

    return None

def decode_def_frame(data, foff, palette):
    """
    Decodes a single frame from DEF file data.
    Returns (PIL.Image or None, frame_info_dict).
    """
    if foff + 32 > len(data):
        return None, {}

    fsize, ffmt, fw, fh, sw, sh, lm, tm = struct.unpack("<IIIIIIii", data[foff:foff+32])
    frame_info = {
        "format": ffmt,
        "full_width": fw,
        "full_height": fh,
        "sprite_width": sw,
        "sprite_height": sh,
        "left_margin": lm,
        "top_margin": tm,
    }

    if sw == 0 or sh == 0 or sw > 4096 or sh > 4096:
        return None, frame_info

    base = foff + 32
    pixels = bytearray(sw * sh)

    try:
        if ffmt == 0:
            # Uncompressed
            raw_len = sw * sh
            if base + raw_len <= len(data):
                pixels[:] = data[base:base+raw_len]
            else:
                return None, frame_info

        elif ffmt == 1:
            # Format 1: row offsets table
            if base + sh * 4 > len(data):
                return None, frame_info
            row_offsets = struct.unpack(f"<{sh}I", data[base:base+sh*4])
            for r in range(sh):
                cur = base + row_offsets[r]
                row_len = 0
                while row_len < sw and cur < len(data):
                    seg_type = data[cur]
                    length = data[cur + 1] + 1
                    cur += 2
                    if seg_type == 0xFF:
                        pixels[r * sw + row_len : r * sw + row_len + length] = data[cur : cur + length]
                        cur += length
                    else:
                        pixels[r * sw + row_len : r * sw + row_len + length] = bytes([seg_type]) * length
                    row_len += length

        elif ffmt == 2:
            # Format 2
            if base + 2 > len(data):
                return None, frame_info
            cur = base + struct.unpack("<H", data[base:base+2])[0]
            for r in range(sh):
                row_len = 0
                while row_len < sw and cur < len(data):
                    seg = data[cur]
                    cur += 1
                    code = seg // 32
                    length = (seg & 31) + 1
                    if code == 7:
                        pixels[r * sw + row_len : r * sw + row_len + length] = data[cur : cur + length]
                        cur += length
                    else:
                        pixels[r * sw + row_len : r * sw + row_len + length] = bytes([code]) * length
                    row_len += length

        elif ffmt == 3:
            # Format 3
            blocks_per_row = max(1, sw // 32)
            table_size = sh * 2 * blocks_per_row
            if base + table_size > len(data):
                return None, frame_info
            for r in range(sh):
                cur = base + struct.unpack("<H", data[base + r * 2 * blocks_per_row : base + r * 2 * blocks_per_row + 2])[0]
                row_len = 0
                while row_len < sw and cur < len(data):
                    seg = data[cur]
                    cur += 1
                    code = seg // 32
                    length = (seg & 31) + 1
                    if code == 7:
                        pixels[r * sw + row_len : r * sw + row_len + length] = data[cur : cur + length]
                        cur += length
                    else:
                        pixels[r * sw + row_len : r * sw + row_len + length] = bytes([code]) * length
                    row_len += length
        else:
            return None, frame_info

        img = Image.frombytes("P", (sw, sh), bytes(pixels))
        if palette and len(palette) >= 768:
            img.putpalette(palette[:768])
        return img, frame_info

    except Exception:
        return None, frame_info

def extract_lod(lod_path, out_dir, manifest, convert_def_frames=True):
    """Extracts all files from a .LOD / .PAC archive."""
    print(f"[*] Extracting LOD: {lod_path.name}")
    with open(lod_path, "rb") as f:
        magic = f.read(4)
        if magic not in (b"LOD\x00", b"PAC\x00"):
            print(f"[!] Warning: invalid LOD magic {magic} in {lod_path}")
            return
        f.seek(8)
        total_files = struct.unpack("<I", f.read(4))[0]
        f.seek(0x5c)
        entries = []
        for _ in range(total_files):
            name_raw = f.read(16)
            name = name_raw.split(b"\x00")[0].decode("latin1", errors="replace").strip()
            offset, full_size, _, comp_size = struct.unpack("<IIII", f.read(16))
            entries.append((name, offset, full_size, comp_size))

        for name, offset, full_size, comp_size in entries:
            f.seek(offset)
            raw = zlib.decompress(f.read(comp_size)) if comp_size else f.read(full_size)
            uname = name.upper()

            file_entry = {
                "archive": lod_path.name,
                "original_name": name,
                "size_bytes": full_size,
            }

            if uname.endswith(".PCX"):
                dest_cat = out_dir / "bitmaps"
                dest_cat.mkdir(parents=True, exist_ok=True)
                img = parse_h3_pcx(raw)
                png_name = f"{Path(name).stem}.png"
                if img:
                    img.save(dest_cat / png_name)
                    file_entry["type"] = "bitmap"
                    file_entry["output_file"] = f"bitmaps/{png_name}"
                    file_entry["dimensions"] = [img.width, img.height]
                    file_entry["mode"] = img.mode
                else:
                    raw_path = dest_cat / name
                    raw_path.write_bytes(raw)
                    file_entry["type"] = "raw_pcx"
                    file_entry["output_file"] = f"bitmaps/{name}"

            elif uname.endswith(".DEF"):
                dest_cat = out_dir / "sprites"
                dest_cat.mkdir(parents=True, exist_ok=True)
                # Always save raw .def
                raw_def_path = dest_cat / name
                raw_def_path.write_bytes(raw)

                file_entry["type"] = "sprite_def"
                file_entry["output_file"] = f"sprites/{name}"

                if convert_def_frames and len(raw) >= 16 + 768:
                    try:
                        dtype, width, height, total_blocks = struct.unpack("<IIII", raw[:16])
                        pal = raw[16:16+768]
                        it = 16 + 768
                        def_stem = Path(name).stem
                        frames_dir = dest_cat / f"{def_stem}_frames"
                        frames_dir.mkdir(exist_ok=True)
                        file_entry["def_type"] = hex(dtype)
                        file_entry["def_width"] = width
                        file_entry["def_height"] = height
                        file_entry["blocks"] = []

                        for b_idx in range(total_blocks):
                            b_id, n_entries = struct.unpack("<II", raw[it:it+8])
                            it += 16
                            frame_names = []
                            for _ in range(n_entries):
                                frame_names.append(raw[it:it+13].split(b"\x00")[0].decode("latin1", errors="replace"))
                                it += 13
                            offsets = struct.unpack(f"<{n_entries}I", raw[it:it+4*n_entries])
                            it += 4 * n_entries

                            block_data = {"block_id": b_id, "frame_count": n_entries, "frames": []}
                            for f_idx, foff in enumerate(offsets):
                                frame_img, finfo = decode_def_frame(raw, foff, pal)
                                fname = frame_names[f_idx] if f_idx < len(frame_names) else f"frame_{b_id}_{f_idx}"
                                png_file = f"{fname}.png"
                                if frame_img:
                                    frame_img.save(frames_dir / png_file)
                                    finfo["file"] = f"sprites/{def_stem}_frames/{png_file}"
                                block_data["frames"].append(finfo)
                            file_entry["blocks"].append(block_data)
                    except Exception as e:
                        file_entry["def_parse_error"] = str(e)

            elif uname.endswith(".TXT") or uname.endswith(".CSV"):
                dest_cat = out_dir / "texts"
                dest_cat.mkdir(parents=True, exist_ok=True)
                dest_file = dest_cat / name
                dest_file.write_bytes(raw)
                file_entry["type"] = "text"
                file_entry["output_file"] = f"texts/{name}"

            else:
                dest_cat = out_dir / "misc"
                dest_cat.mkdir(parents=True, exist_ok=True)
                dest_file = dest_cat / name
                dest_file.write_bytes(raw)
                file_entry["type"] = "misc"
                file_entry["output_file"] = f"misc/{name}"

            manifest.append(file_entry)

def extract_snd(snd_path, out_dir, manifest):
    """Extracts all WAV sounds from a .SND archive."""
    print(f"[*] Extracting SND: {snd_path.name}")
    dest_cat = out_dir / "sounds"
    dest_cat.mkdir(parents=True, exist_ok=True)

    with open(snd_path, "rb") as f:
        total_files = struct.unpack("<I", f.read(4))[0]
        entries = []
        for _ in range(total_files):
            name_raw = f.read(40)
            name = name_raw.split(b"\x00")[0].decode("ascii", errors="replace").strip()
            if not name.lower().endswith(".wav"):
                name += ".wav"
            offset, size = struct.unpack("<II", f.read(8))
            entries.append((name, offset, size))

        for name, offset, size in entries:
            f.seek(offset)
            data = f.read(size)
            out_file = dest_cat / name
            out_file.write_bytes(data)
            manifest.append({
                "archive": snd_path.name,
                "original_name": name,
                "type": "audio",
                "output_file": f"sounds/{name}",
                "size_bytes": size,
            })

def extract_vid(vid_path, out_dir, manifest):
    """Extracts all SMK/BIK videos from a .VID archive."""
    print(f"[*] Extracting VID: {vid_path.name}")
    dest_cat = out_dir / "videos"
    dest_cat.mkdir(parents=True, exist_ok=True)

    with open(vid_path, "rb") as f:
        total_files = struct.unpack("<I", f.read(4))[0]
        entries = []
        for _ in range(total_files):
            name_raw = f.read(40)
            name = name_raw.split(b"\x00")[0].decode("ascii", errors="replace").strip()
            offset = struct.unpack("<I", f.read(4))[0]
            entries.append((name, offset))

        f.seek(0, os.SEEK_END)
        total_size = f.tell()

        sorted_offsets = sorted(set(e[1] for e in entries))
        offset_to_next = {}
        for idx, off in enumerate(sorted_offsets):
            nxt = sorted_offsets[idx + 1] if idx + 1 < len(sorted_offsets) else total_size
            offset_to_next[off] = nxt

        for name, offset in entries:
            next_offset = offset_to_next.get(offset, total_size)
            size = max(0, next_offset - offset)
            f.seek(offset)
            data = f.read(size)
            out_file = dest_cat / name
            out_file.write_bytes(data)
            manifest.append({
                "archive": vid_path.name,
                "original_name": name,
                "type": "video",
                "output_file": f"videos/{name}",
                "size_bytes": size,
            })

def main():
    parser = argparse.ArgumentParser(description="LibreVCMI Game Data Extractor")
    parser.add_argument("--data-dir", default=os.path.expanduser("~/.local/share/vcmi/Data"), help="Path to VCMI Data directory")
    parser.add_argument("--out-dir", default="extracted_assets", help="Output directory")
    parser.add_argument("--no-def-frames", action="store_true", help="Skip converting DEF animation frames to individual PNGs")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists():
        print(f"[!] Error: Data directory {data_dir} does not exist!")
        sys.exit(1)

    print(f"=== LibreVCMI Asset Extractor ===")
    print(f"Source: {data_dir}")
    print(f"Target: {out_dir}\n")

    manifest = []

    # 1. Process LOD files
    for lod_file in sorted(data_dir.glob("*.lod")) + sorted(data_dir.glob("*.LOD")):
        extract_lod(lod_file, out_dir, manifest, convert_def_frames=not args.no_def_frames)

    # 2. Process SND files
    for snd_file in sorted(data_dir.glob("*.snd")) + sorted(data_dir.glob("*.SND")):
        extract_snd(snd_file, out_dir, manifest)

    # 3. Process VID files
    for vid_file in sorted(data_dir.glob("*.vid")) + sorted(data_dir.glob("*.VID")):
        extract_vid(vid_file, out_dir, manifest)

    # Save manifest
    manifest_path = out_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Generate summary stats
    type_counts = {}
    for item in manifest:
        t = item.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    summary_md = f"""# LibreVCMI Asset Manifest

Projekt: **LibreVCMI**
Data wyodrębnienia: {os.uname().nodename}

## Podsumowanie zasobów:
- Łącznie zasobów: **{len(manifest)}**
"""
    for t, count in sorted(type_counts.items()):
        summary_md += f"- **{t}**: {count} plików\n"

    summary_md += """
## Struktura katalogów:
- `bitmaps/` - grafiki interfejsu, ikonki, portrety, tła ekranów (skonwertowane z PCX na PNG)
- `sprites/` - pliki animacji DEF oraz wyodrębnione klatki animacji PNG
- `sounds/` - efekty dźwiękowe WAV
- `texts/` - konfiguracje i tabele tekstowe TXT
- `videos/` - przerywniki filmowe SMK/BIK
- `manifest.json` - pełna baza metadanych każdego zasobu
"""
    (out_dir / "README.md").write_text(summary_md, encoding="utf-8")

    print("\n=== Sukces! Wyodrębnianie zakończone ===")
    print(f"Liczba zasobów: {len(manifest)}")
    for t, count in sorted(type_counts.items()):
        print(f" - {t}: {count}")
    print(f"Manifest zapisano w: {manifest_path}")

if __name__ == "__main__":
    main()
