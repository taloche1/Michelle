from __future__ import absolute_import

import requests
import zipfile
import errno
import os
import json
import datetime
import settings



class AutoUpdater(object):
    #REPO = "lekeno/EDR"
    REPO = "taloche1/Michelle"
    UPDATES = os.path.join(os.path.dirname(__file__),'updates')
    LATEST = os.path.join(UPDATES, 'latest.zip')
    BACKUP = os.path.join(os.path.dirname(__file__),'backup')
    EDR_PATH = os.path.abspath(os.path.dirname(__file__))

    def __init__(self):
        self.updates = AutoUpdater.UPDATES
        self.output = AutoUpdater.LATEST
        

    def download_latest(self):
        if not os.path.exists(self.updates):
            try:
                os.makedirs(self.updates)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    return False

        download_url = self.__latest_release_url()
        if not download_url:
            return False
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        if response.status_code != requests.codes.ok:
            return False

        with open(self.output, 'wb') as handle:
            for block in response.iter_content(32768):
                handle.write(block)
        return True

    def clean_old_backups(self):
        files = os.listdir(AutoUpdater.BACKUP)
        files = [os.path.join(AutoUpdater.BACKUP, f) for f in files]
        files.sort(key=lambda x: os.path.getctime(x))
        nbfiles = len(files)
        max_backups = 2
        for i in range(0, nbfiles - max_backups):
            f = files[i]
            settings.logger.warning(f"Removing backup {f}")
            os.unlink(f)

    def clean_update(self):
        os.rmdir(self.updates)

    def make_backup(self):
        if not os.path.exists(AutoUpdater.BACKUP):
            try:
                os.makedirs(AutoUpdater.BACKUP)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    return False
        name = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + '.zip'
        backup_file = os.path.join(AutoUpdater.BACKUP, name)
        zipf = zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED)
        self.__zipdir(AutoUpdater.EDR_PATH, zipf)
        zipf.close()

    def __zipdir(self, path, ziph):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if (("updates" not in d) and ("backup" not in d) and (".git" not in d) and (".vs" not in d))]
            for file in files:
                if file.endswith(".pyc") or file.endswith(".pyo"):
                    continue
                fp = os.path.join(root, file)
                ziph.write(fp, os.path.relpath(fp, AutoUpdater.EDR_PATH))

    def extract_latest(self):
        with zipfile.ZipFile(self.output, "r") as latest:
            latest.extractall(AutoUpdater.EDR_PATH)

    def __latest_release_url(self):
        latest_release_api = "https://api.github.com/repos/{}/releases/latest".format(self.REPO)
        response = requests.get(latest_release_api)
        if response.status_code != requests.codes.ok:
            settings.logger.warning(f"Couldn't check the latest release on github: {response.status_code}")
            return None
        json_resp = json.loads(response.content)
        asset = json_resp.get("assets", None)
        if not asset:
            return None
        return asset[0].get("browser_download_url", None)

    def get_version(self):
        latest_release_api = "https://api.github.com/repos/{}/releases/latest".format(self.REPO)
        response = requests.get(latest_release_api)
        if response.status_code != requests.codes.ok:
            settings.logger.warning(f"Couldn't check the latest release on github: {response.status_code}")
            return None
        json_resp = json.loads(response.content)
        tag = json_resp.get("tag_name", None)
        return tag

