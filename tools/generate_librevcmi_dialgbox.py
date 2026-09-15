import struct
import numpy as np
from PIL import Image

# Load original palette
with open('/home/fervi/LibreVCMI/extracted_assets/sprites/dialgbox.def', 'rb') as f:
    orig_def = f.read()

orig_pal = orig_def[16:784]

# Carved Dark Walnut / Oak moulding profile
# Outer edge -> Outer wood bevel -> Groove -> Inner wood moulding -> Ribbon -> Inner wood bead -> Seam
#
# Wood palette indices:
# Dark shadow: 188 (RGB 40, 30, 0), 190 (RGB 36, 27, 0)
# Dark wood base: 174 (RGB 72, 51, 26), 170 (RGB 79, 60, 10)
# Mid wood: 154 (RGB 95, 77, 29), 135 (RGB 131, 104, 31)
# Light wood bevel highlight: 120 (RGB 146, 119, 45), 101 (RGB 161, 134, 61)
# Groove / crevice: 222 (RGB 0, 0, 0)
# Player ribbon: 236, 238, 240 (royal blue / player colors)
# Inner shadow: 191 (RGB 33, 25, 5)

# Horizontal top (15 rows):
# y=0:  190 (Outer dark seam)
# y=1:  101 (Top carved wood bevel highlight)
# y=2:  135 (Warm oak mid-tone)
# y=3:  174 (Walnut shade)
# y=4:  222 (Carved groove)
# y=5:  120 (Inner wood rib highlight)
# y=6:  154 (Wood tone)
# y=7:  184 (Shaded wood recess)
# y=8:  236 (Ribbon top shadow)
# y=9:  238 (Ribbon mid tone)
# y=10: 240 (Ribbon bright center)
# y=11: 238 (Ribbon mid tone)
# y=12: 236 (Ribbon bottom shadow)
# y=13: 135 (Inner wood rounded bead)
# y=14: 191 (Inner drop shadow onto dialog content)

row_t = [190, 101, 135, 174, 222, 120, 154, 184, 236, 238, 240, 238, 236, 135, 191]

# Horizontal bottom (15 rows - inverted vertically):
row_b = [191, 135, 236, 238, 240, 238, 236, 184, 154, 120, 222, 174, 135, 101, 190]

# Vertical left (14 cols):
col_l = [190, 101, 135, 174, 222, 120, 154, 184, 236, 238, 240, 236, 135, 191]

# Vertical right (14 cols - inverted horizontally):
col_r = [191, 135, 236, 240, 238, 236, 184, 154, 120, 222, 174, 135, 101, 190]

# Construct DiBoxT (64x15):
arr_t = np.zeros((15, 64), dtype=np.uint8)
for y in range(15):
    arr_t[y, :] = row_t[y]

# Add subtle wood grain variation along x
np.random.seed(123)
for x in range(64):
    grain = (x * 3) % 17
    if grain in (0, 1):
        arr_t[2, x] = 124 # subtle grain highlight
        arr_t[6, x] = 135
    elif grain in (5, 6):
        arr_t[2, x] = 154 # subtle grain shadow
        arr_t[3, x] = 184
    if x % 16 in (0, 1, 2):
        arr_t[9:11, x] = 244 # ribbon shimmer

# Construct DiBoxB (64x15):
arr_b = np.zeros((15, 64), dtype=np.uint8)
for y in range(15):
    arr_b[y, :] = row_b[y]
for x in range(64):
    grain = (x * 3) % 17
    if grain in (0, 1):
        arr_b[12, x] = 124
        arr_b[8, x] = 135
    elif grain in (5, 6):
        arr_b[12, x] = 154
        arr_b[11, x] = 184
    if x % 16 in (0, 1, 2):
        arr_b[4:6, x] = 244

# Construct DiBoxL (14x64):
arr_l = np.zeros((64, 14), dtype=np.uint8)
for x in range(14):
    arr_l[:, x] = col_l[x]
for y in range(64):
    grain = (y * 3) % 17
    if grain in (0, 1):
        arr_l[y, 2] = 124
        arr_l[y, 6] = 135
    elif grain in (5, 6):
        arr_l[y, 2] = 154
        arr_l[y, 3] = 184
    if y % 16 in (0, 1, 2):
        arr_l[y, 9:11] = 244

# Construct DiBoxR (14x64):
arr_r = np.zeros((64, 14), dtype=np.uint8)
for x in range(14):
    arr_r[:, x] = col_r[x]
for y in range(64):
    grain = (y * 3) % 17
    if grain in (0, 1):
        arr_r[y, 11] = 124
        arr_r[y, 7] = 135
    elif grain in (5, 6):
        arr_r[y, 11] = 154
        arr_r[y, 10] = 184
    if y % 16 in (0, 1, 2):
        arr_r[y, 3:5] = 244

# Construct DiBoxTL (64x64):
arr_tl = np.zeros((64, 64), dtype=np.uint8)
# Top border into TL
for y in range(15):
    for x in range(64):
        arr_tl[y, x] = row_t[y]

# Left border into TL
for x in range(14):
    for y in range(64):
        arr_tl[y, x] = col_l[x]

# Miter joint corner
for y in range(15):
    for x in range(14):
        if x >= y:
            arr_tl[y, x] = row_t[y]
        else:
            arr_tl[y, x] = col_l[x]

# Carved Celtic/Floral wooden corner boss (stud) at junction:
# Center around (14, 15) with wooden carvings extending inward:
stud = [
    # Carved wooden corner bracket / rosette
    (14, 15, 135), (15, 15, 101), (16, 15, 135), (17, 15, 174), (18, 15, 222),
    (14, 16, 101), (15, 16, 97),  (16, 16, 101), (17, 16, 135), (18, 16, 174), (19, 16, 222),
    (14, 17, 135), (15, 17, 101), (16, 17, 135), (17, 17, 154), (18, 17, 184), (19, 17, 222),
    (14, 18, 174), (15, 18, 135), (16, 18, 154), (17, 18, 184), (18, 18, 222),
    (14, 19, 222), (15, 19, 174), (16, 19, 184), (17, 19, 222),
    (14, 20, 222), (15, 20, 222)
]
for ox, oy, c in stud:
    arr_tl[oy, ox] = c

# Flips for other corners
arr_tr = np.fliplr(arr_tl).copy()
arr_bl = np.flipud(arr_tl).copy()
arr_br = np.flipud(arr_tr).copy()

# Status bar
arr_rl = arr_bl.copy()
arr_rr = arr_br.copy()
arr_rb = np.zeros((36, 64), dtype=np.uint8)
for y in range(36):
    arr_rb[y, :] = arr_b[min(y, 14), :]

frames = [
    {'name': 'DiBoxTL.pcx', 'full_width': 64, 'full_height': 64, 'width': 64, 'height': 64, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_tl.tobytes()},
    {'name': 'DiBoxTR.pcx', 'full_width': 64, 'full_height': 64, 'width': 64, 'height': 64, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_tr.tobytes()},
    {'name': 'DiBoxBL.pcx', 'full_width': 64, 'full_height': 64, 'width': 64, 'height': 64, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_bl.tobytes()},
    {'name': 'DiBoxBR.pcx', 'full_width': 64, 'full_height': 64, 'width': 64, 'height': 64, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_br.tobytes()},
    {'name': 'DiBoxL.pcx',  'full_width': 64, 'full_height': 64, 'width': 14, 'height': 64, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_l.tobytes()},
    {'name': 'DiBoxR.pcx',  'full_width': 64, 'full_height': 64, 'width': 14, 'height': 64, 'left_margin': 50, 'top_margin': 0, 'pixels': arr_r.tobytes()},
    {'name': 'DiBoxT.pcx',  'full_width': 64, 'full_height': 64, 'width': 64, 'height': 15, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_t.tobytes()},
    {'name': 'DiBoxB.pcx',  'full_width': 64, 'full_height': 64, 'width': 64, 'height': 15, 'left_margin': 0, 'top_margin': 49, 'pixels': arr_b.tobytes()},
    {'name': 'DiBoxRL.pcx', 'full_width': 64, 'full_height': 64, 'width': 64, 'height': 64, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_rl.tobytes()},
    {'name': 'DiBoxRR.pcx', 'full_width': 64, 'full_height': 64, 'width': 64, 'height': 64, 'left_margin': 0, 'top_margin': 0, 'pixels': arr_rr.tobytes()},
    {'name': 'DiBoxRB.pcx', 'full_width': 64, 'full_height': 64, 'width': 64, 'height': 36, 'left_margin': 0, 'top_margin': 28, 'pixels': arr_rb.tobytes()},
]

num_frames = len(frames)
type_ = 0x47 # type 71
header = struct.pack('<IIII', type_, 64, 64, 1)
block_header = struct.pack('<IIII', 0, num_frames, 0, 0)
entries_names = b''
for f in frames:
    entries_names += f['name'].encode('ascii')[:12].ljust(13, b'\x00')

offsets_size = num_frames * 4
data_start = 16 + 768 + 16 + (num_frames * 13) + offsets_size

frame_offsets = []
frames_data = b''
for f in frames:
    frame_offsets.append(data_start + len(frames_data))
    pixels = f['pixels']
    fhdr = struct.pack('<IIIIiiii', len(pixels), 0, f['full_width'], f['full_height'], f['width'], f['height'], f['left_margin'], f['top_margin'])
    frames_data += fhdr + pixels

offsets_data = struct.pack(f'<{num_frames}I', *frame_offsets)
def_bytes = header + orig_pal + block_header + entries_names + offsets_data + frames_data

# Save to LibreVCMI game mod
out_path = '/home/fervi/.local/share/vcmi/Mods/librevcmi/Content/Sprites/dialgbox.def'
with open(out_path, 'wb') as f:
    f.write(def_bytes)

# Save to repo
repo_path = '/home/fervi/LibreVCMI-repo/Mods/librevcmi/Content/Sprites/dialgbox.def'
with open(repo_path, 'wb') as f:
    f.write(def_bytes)

print('Carved wood dialgbox.def successfully generated and written!')
