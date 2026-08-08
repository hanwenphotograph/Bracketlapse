<p align="center">
  <img src="res/title.jpg" alt="Bracketlapse" width="60%">
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README_CN.md">简体中文</a>
</p>

# Bracketlapse

Bracketlapse is a cross-platform command line tool for bracketed timelapse work:

- Fuse every 3 JPG files into one exposure-fused HDR-looking frame with Hugin `enfuse`.
  The default `enfuse` settings use `--exposure-width=0.05`, `--exposure-optimum=0.30`,
  `--saturation-weight=0`, and `--contrast-weight=0`.
- Optionally align each bracket group with Hugin `align_image_stack`.
- Deflicker the fused frame sequence with `simple-deflicker`, then create an
  HEVC/H.265 MP4 timelapse from the deflickered frames with `ffmpeg`.
- Especially useful for Nikon and FUJIFILM cameras, because they can automatically shoot bracketed exposures during timelapse capture. This program was tested with my own Nikon Z30.

<p align="center">
  <img src="res/z30_cn.jpg" alt="Nikon Z30 bracketing settings in Chinese" width="33%">
  <img src="res/z30_en.jpg" alt="Nikon Z30 bracketing settings in English" width="33%">
</p>

It runs on Windows and macOS with Python 3.10+.

## Requirements

Bracketlapse checks the selected pipeline at startup and tries to prepare
missing tools automatically.

Required runtime tools:

- Hugin command line tools: `enfuse`, and optionally `align_image_stack`.
- `simple-deflicker` from the `master` branch.
- `ffmpeg`.

Automatic setup uses a local package manager when available: Homebrew on macOS,
winget or Chocolatey on Windows, and apt/dnf/pacman on Linux. If
`simple-deflicker` is missing, Bracketlapse clones the `master` branch and
builds it into `~/.cache/bracketlapse/tools/bin`, which requires `git` and Go.
If a required tool cannot be prepared automatically, Bracketlapse stops before
processing starts and reports the missing tool.

On Windows, if Hugin is installed at `D:\Medias\Hugin\bin`, add that directory to your user `PATH`.

## Install for Development

From this repository:

```powershell
python -m pip install -e .
```

On macOS, use `python3` if `python` is not available:

```bash
python3 -m pip install -e .
```

## Usage

Fuse bracketed JPG files in a directory, then automatically create a video:

```bash
bracketlapse "E:\Medias\Images\example"
```

If you do not pass any arguments, Bracketlapse prints the full help text:

```bash
bracketlapse
```

Standby mode watches one directory and immediately fuses each newly completed bracket group while capture continues. After the recursive entry count remains unchanged for `QUIET_SECONDS`, it fills any missing HDR frames, runs deflicker once, and exports the final video:

```bash
bracketlapse --standby WATCH_DIR TARGET_DIR QUIET_SECONDS [loop]
```

In-place standby (`WATCH_DIR == TARGET_DIR`) streams HDR frames without launching a new Bracketlapse process for every group. A successful frame emits one machine-readable line for orchestrators:

```text
BRACKETLAPSE_EVENT {"event":"hdr_ready","frame_number":1,"path":"/absolute/path/to/frame.jpg"}
```

When the watch and target directories differ, Bracketlapse preserves the dated-folder behavior and starts processing after the quiet interval.

If a folder named like `20260609` already exists, the next one becomes `20260609-1`, then `20260609-2`, and so on.

When the input filenames contain a numeric sequence and one or more numbers are missing, the incomplete HDR group is skipped, later groups stay aligned, and a warning is printed.

If you run Bracketlapse from a directory that contains image subdirectories, which is common because camera storage formats usually enforce strict limits on the maximum number of photos in a single folder, it asks whether to merge multiple subdirectories. In merge mode, the selected subdirectories are used as input, while `hdr_enfuse`, `hdr_deflick`, and `hdr_video` are still created in the current working directory.

<p align="center">
  <img src="res/multi_folders.png" alt="Multiple image folders" width="66%">
</p>

Merge all detected image subdirectories:

```bash
bracketlapse --merge-subdirs
```

Merge specific subdirectories:

```bash
bracketlapse --merge-dirs part1 part2 part3
```

Ignore subdirectories and process only the chosen directory:

```bash
bracketlapse --no-merge-subdirs
```

By default it sorts files by name and processes every 3 JPG files as one group:

```text
DSC_0480.JPG, DSC_0481.JPG, DSC_0482.JPG -> hdr_00001.jpg
DSC_0483.JPG, DSC_0484.JPG, DSC_0485.JPG -> hdr_00002.jpg
```

If the total number of input files is not divisible by the group size, Bracketlapse drops the final leftover file(s), prints a warning, and continues processing the complete groups.

The default fused-frame output directory is `hdr_enfuse` inside the processing directory.
The default deflickered-frame output directory is `hdr_deflick` inside the processing directory.
The final video is created from `hdr_deflick` at `hdr_video/hdr_timelapse.mp4`. Videos are encoded as HEVC/H.265.

Use alignment when the camera moved between the bracketed shots:

```bash
bracketlapse "E:\Medias\Images\example" --align
```

Test only the first few groups:

```bash
bracketlapse "E:\Medias\Images\example" --limit 3 --overwrite
```

Run fusion and deflicker, but skip automatic video creation:

```bash
bracketlapse "E:\Medias\Images\example" --no-video
```

Skip deflicker and create the video from fused frames directly:

```bash
bracketlapse "E:\Medias\Images\example" --no-deflick
```

Choose video settings for the automatic video:

```bash
bracketlapse "E:\Medias\Images\example" --fps 30 --video-output hdr_video\hdr_timelapse.mp4
```

Choose simple-deflicker settings:

```bash
bracketlapse "E:\Medias\Images\example" --deflick-rolling-average 15 --deflick-jpeg-compression 95
```

Print debug logs and create an extra pre-deflicker HDR video:

```bash
bracketlapse "E:\Medias\Images\example" --debug
```

This writes `hdr_video/hdr_timelapse_hdr_debug.mp4` before deflicker starts.

If the executable is not named `simple-deflicker` or is not in `PATH`, pass it explicitly:

```bash
bracketlapse "E:\Medias\Images\example" --deflick-bin "D:\Tools\simple-deflicker.exe"
```

Create a video manually from an existing JPG frame directory:

```bash
bracketlapse video "E:\Medias\Images\example\hdr_enfuse" --fps 30 --output hdr_timelapse.mp4
```

Run `video` without extra arguments to print the video command help:

```bash
bracketlapse video
```

Update runtime dependencies:

```bash
bracketlapse update
```

Update only `simple-deflicker`:

```bash
bracketlapse update simple-deflicker
```

## Useful Options

```bash
bracketlapse --help
bracketlapse video --help
```

Important options:

- `--sort name|time`: choose filename sorting or modified-time sorting.
- `--output PATH`: write output to a custom directory or file.
- `--merge-subdirs`: merge all detected image subdirectories.
- `--merge-dirs DIR...`: merge specific subdirectories.
- `--no-merge-subdirs`: ignore subdirectories and process only the chosen directory.
- `--overwrite`: replace existing output.
- `--align`: align bracket groups before exposure fusion.
- `--ext jpg|tif`: choose fused frame extension.
- `--no-video`: skip automatic video creation after fusion and deflicker.
- `--no-deflick`: skip simple-deflicker processing and use fused frames directly.
- `--fps`: video frames per second.
- `--video-output PATH`: automatic video output path.
- `--deflick-output PATH`: deflickered frame output directory.
- `--deflick-bin PATH`: simple-deflicker executable name or path.
- `--deflick-rolling-average`, `--deflick-jpeg-compression`, and `--deflick-threads`: simple-deflicker settings.
- `--debug`: print debug logs and create an extra pre-deflicker HDR video.
- `--crf` and `--preset`: x265 quality and speed settings for video encoding.

## License

Bracketlapse is licensed under the GNU General Public License v3.0 or later. See [LICENSE](LICENSE) for details.
