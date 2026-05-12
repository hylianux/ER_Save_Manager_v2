import subprocess, os, zipfile, requests, time
from os_layer import copy_folder, delete_folder


version_url = "https://github.com/RorikSR/ER_Save_Manager_v2/releases/latest"
update_dir = "./data/updates/"


def get_latest_release():
    try:
        r = requests.get(version_url, timeout=10)  # Get redirect url
        r.raise_for_status()
        tag = r.url.rstrip("/").split("/")[-1]
        version = tag.lstrip("v")
        return version, f"https://github.com/RorikSR/ER_Save_Manager_v2/releases/download/{tag}/EldenRing-Save-Manager-v{version}-portable.zip"
    except Exception as exc:
        print(f"Could not check for updates: {exc}")
        return None, None


def update(update_url):
    if update_url is None:
        print("No release is available yet, or GitHub could not be reached.")
        return

    if os.path.isdir(update_dir) is False:
        os.mkdir(update_dir)

    comm1 = f"curl -L {update_url} > {update_dir}upd.zip"

    subprocess.run(comm1, shell=True, text=True)
    with zipfile.ZipFile(f"{update_dir}/upd.zip", "r") as fh:
        fh.extractall(f"{update_dir}/upd")

    copy_folder(f"{update_dir}upd", "./")
    os.remove(f"{update_dir}upd.zip")
    delete_folder(f"{update_dir}upd")


def main():
    print("--- Self Update ---\n")
    ver, update_url = get_latest_release()
    if ver is None:
        time.sleep(3)
        raise SystemExit(1)

    inp = input(f"Install Latest Elden Ring Save Manager v{str(ver)}?  (yes/no): ")
    if inp.lower() in ["yes", "y"]:
        print(f"\nDownloading From: {update_url}\n")
        update(update_url)
        print("Finished")
        time.sleep(5)
    else:
        print("Cancelled")
        time.sleep(1)

if __name__ == "__main__":
    main()
