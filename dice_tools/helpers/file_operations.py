import os
import re
import shutil


class FileOperations:
    """
    Helper class for Application with basic file operations.
    """
    @staticmethod
    def rmtree(path, ignore_errors=True, on_error=None):
        """
        Removes directory tree under path recursively.

        :param path: Top of directory tree.
        :param ignore_errors: Do not raise exception on errors.
        :param on_error: Function with arguments (func, path, exc_info) where
            func is platform and implementation dependent; path is the argument
            to that function that caused it to fail; and exc_info is a tuple
            returned by sys.exc_info(). If on_error is not None and
            ignore_errors is True on_error will be called each time error
            occurs.
        """
        shutil.rmtree(path, ignore_errors, on_error)

    @staticmethod
    def rm(path):
        """
        Removes file object by calling os.unlink.

        :param path: Path to file object.
        """
        os.unlink(path)

    @staticmethod
    def clear_folder_content(path):
        """
        Removes files from directory path.

        :param path: Path to directory to clear contents of.
        """
        FileOperations.rmtree(path)
        FileOperations.make_dir(path)

    @staticmethod
    def move(src, dst):
        """
        Recursively move a file or directory to another location.

        :param src: Source path.
        :param dst: Destination path. If the destination is a directory or a
            symlink to a directory, the source is moved inside the directory.
            The destination path must not already exist.
        """
        shutil.move(src, dst)

    @staticmethod
    def make_dir(dir, exist_ok=True, ignore_errors=True):
        """
        Creates directory.
        :param dir: Path to directory been created.
        :param exist_ok: Do not raise exception If True.
        :param ignore_errors: Do not raise exception on error.
        """
        if ignore_errors:
            try:
                os.makedirs(dir, exist_ok=exist_ok)
            except:
                pass
        else:
            os.makedirs(dir, exist_ok=exist_ok)

    @staticmethod
    def parse_url(url):
        """
        Parses url and cuts "file://" when path to file returned from QML.

        :param url: Url to parse.
        :return: Url suitable to use in Python.
        """
        if url.startswith("file://"):
            url = re.split("^(file:/{2,3})(.:/.*|/.*)", url)[2]
        return url

    @staticmethod
    def touch(file_name, times=None):
        """
        Sets the access and modified time of file. If file does not exists,
            creates it.

        :param file_name: Path to file.
        :param times: If times is not None, it must be a tuple (atime, mtime);
            atime and mtime should be expressed as float seconds since the
            epoch. If times is None, the current time is used.
        """
        with open(file_name, 'a'):
            os.utime(file_name, times)

    @staticmethod
    def copy_merge(src, dst):
        """
        Merges a directory from src into dst by copying src into dst.
        If a file in dst already exists, it is overwritten by the file in src.
        Directories inside src are handled recursively.
        """
        if not os.path.exists(dst):
            FileOperations.make_dir(dst)

        src_list = os.listdir(src)
        dst_list = os.listdir(dst)

        for f in src_list:
            dst_path = os.path.join(dst, f)
            src_path = os.path.join(src, f)
            if os.path.exists(dst_path):
                if os.path.isdir(dst_path):
                    FileOperations.copy_merge(src_path, dst_path)
                else:
                    # os.unlink(dst_path)
                    # shutil.copy overwrites files by itself
                    shutil.copy(src_path, dst_path)
            else:
                FileOperations.copy(src_path, dst_path) # copy regardless of src_path being a file or directory

    @staticmethod
    def copy(src, dst, merge = False):
        # need to trim src if it has a trailing /, basename will fail otherwise
        if src[-1] == "/": src = src[:-1]
        src_base = os.path.basename(src)
        src_in_dst = os.path.join(dst, src_base)

        if not os.path.exists(dst):
            FileOperations.make_dir(dst)

        if merge:
            FileOperations.copy_merge(src, src_in_dst)
            return

        if os.path.isdir(src):
            shutil.copytree(src, src_in_dst)
        else:
            shutil.copy(src, dst)

    @staticmethod
    def copy_folder_content(src, dest, ignore=None, overwrite=False):
        if os.path.isdir(src):
            if not os.path.isdir(dest):
                os.makedirs(dest)
            files = os.listdir(src)
            if ignore is not None:
                ignored = ignore(src, files)
            else:
                ignored = set()
            for f in files:
                if f not in ignored:
                    FileOperations.copy_folder_content(os.path.join(src, f),
                                             os.path.join(dest, f),
                                             ignore, overwrite=overwrite)
        else:
            if overwrite or not os.path.isfile(dest):
                shutil.copyfile(src, dest)