#!/usr/bin/env python3
# -- coding: utf-8 --
import argparse
import os
import shutil
import subprocess
import ctypes


class Restorer(object):
    def __init__(self, gitlab_path, output_path, with_wiki, overwrite):
        self.gitlab_path = gitlab_path
        self.output_path = output_path
        self.with_wiki = with_wiki
        self.overwrite = overwrite
        self.history = []
        try:
            self.__make_hidden_w32 = ctypes.windll.kernel32.SetFileAttributesW
        except AttributeError:
            self.__make_hidden_w32 = None
        pass

    @staticmethod
    def __call_command(command, command_args):
        subprocess.run([command, *command_args])

    @staticmethod
    def __is_gitlab_repo(full_path):
        return full_path.endswith('.git') and os.path.isfile(
            os.path.join(full_path, 'config')) and os.path.isdir(os.path.join(full_path, 'objects'))

    def __make_hidden(self, pathname):
        if self.__make_hidden_w32:
            self.__make_hidden_w32(pathname, 2)

    def __try_recover_repo(self, maybe_repo_path):
        if self.__is_gitlab_repo(maybe_repo_path) and (not maybe_repo_path.endswith('.wiki.git') or self.with_wiki):
            dest_path = os.path.join(self.output_path, os.path.sep.join(self.history)).removesuffix('.git')
            git_path = os.path.join(dest_path, '.git')
            if os.path.isdir(dest_path) and not self.overwrite:
                raise ValueError('{} already exists'.format(dest_path))
            os.makedirs(dest_path, exist_ok=True)
            shutil.rmtree(git_path, ignore_errors=True)
            shutil.copytree(maybe_repo_path, git_path)
            self.__make_hidden(git_path)
            os.chdir(dest_path)
            self.__call_command('git', ['init'])
            self.__call_command('git', ['reset', '--hard'])
            return True
        return False

    def __walk(self, base_path):
        for root, dirs, _ in os.walk(base_path):
            for d in dirs:
                self.history.append(d)
                sub_dir = os.path.join(root, d)
                try:
                    if self.__try_recover_repo(sub_dir):
                        continue
                    self.__walk(sub_dir)    
                except ValueError as ve:
                    print(ve)
                finally:
                    self.history.pop()

    def run(self):
        self.__walk(self.gitlab_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Restore local git repo from gitlab repo')
    parser.add_argument('gitlab_path', type=str, help='gitlab repo path')
    parser.add_argument('output_path', type=str, help='target path for recovered repos')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--with-wiki', '-w', action='store_true')
    args = parser.parse_args()
    try:
        Restorer(args.gitlab_path, args.output_path, args.with_wiki, args.overwrite).run()
    except Exception as e:
        print(e)
        exit(-1)
    pass
