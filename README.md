# mplus-exporter
Python scripts for exporting via the API for Zetcom's MuseumPlus to DigitalOcean Spaces.
This setup is tailored for MfK's ([Museum of Communication, Bern](https://mfk.ch)) MuseumPlus instance. It provides images and object metadata to MfK's [Online Portal](https://mfk.rechercheonline.ch)

Requires Python and poetry.

## Setup and running
1. Clone this repo.
2. Create `.env` or corresponding environment variables with correct credentials:
    ```bash
    mplus-user="user"
    mplus-pass="pass"
    s3-access-key="access-key"
    s3-secret-key="secret-key"
    ```
3. Update `config/s3.yml` for the correct DigitalOcean Spaces.
4. Dependencies are managed with poetry. After setting up Python and poetry run 
    ```bash
    poetry install
    ```
5. Run exporters using poetry like so: 
    ```bash
    poetry run python img_export.py
    poetry run python json_export.py
    ```

## How it works
The exporters use `mpluspy` to query the MuseumPlus API. The rewuests are preconfigured in the `config` folder. Two different exporters are provided:

**img_export:**
Exports extra-large thumbnails of all public digital assets of a MuseumPlus Instance. The images are saved in a predfined folder (`extra_large`).
The exporter only processes images changed since the last run. Images to be processed are saved to a list first. This allows the exporter to pick up where it left the last time after an interruption.

**json_export:**
Exports all public objects to json using an export template defined in MuseumPlus. The jsons are saved in a predefinde folder (`zetcom-objects`).
The exporter is querying pages of 10000 objects at once and only runs between 18.00 and 08.00 the next day. This ensures no performance issues with MuseumPlus during office hours.

## Scheduling Cronjob
To automatically run the exporters define cronjobs by editing the crontab file (by running `crontab -e`):

```bash
# Initiates JSON-Export every Saturday at 17:55
55 17 * * 6 cd /path/to/repo && /path/to/poetry run python json_export.py
# Initiates Images Export every Friday at 20:00
0 20 * * 5 cd /path/to/repo && /path/to/poetry run python img_export.py

```

To get the path to poetry run `which poetry`
