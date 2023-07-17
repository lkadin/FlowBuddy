from __future__ import annotations
import json
from typing import Literal
import requests
import os


FILE_PATH = os.path.join(os.path.dirname(__file__), "save.json")


# If there are any exceptions related to JSON decoding, file not found, or missing keys,
# a save file is created using the FS module.
try:
    with open(FILE_PATH) as f:
        data = json.load(f)
    _, _, _ = data["settings"], data["groups"], data["tasks"]
except (json.JSONDecodeError, FileNotFoundError, KeyError):
    with open(FILE_PATH, 'w') as f:
        f.write('{"settings": {}, "groups": {}, "tasks": {}}')


class NotFound(Exception):
    def __init__(self, name: str):
        super().__init__(f"'{name}' not found")


class Found(Exception):
    def __init__(self, name: str):
        super().__init__(f"'{name}' already exists")


class NoTasks(Exception):
    def __init__(self, group_name: str):
        super().__init__(f"No tasks found in {group_name}")


class TaskNotFoundInGroup(Exception):
    def __init__(self, group_name: str, task_id: str):
        super().__init__(f"Task {task_id} not found in {group_name}")


class TaskAlreadyInGroup(Exception):
    def __init__(self, group_name: str, task_id: str):
        super().__init__(f"Task {task_id} is already a member of {group_name}")


class NotFoundInFile(Exception):
    def __init__(self, _id: str):
        super().__init__(f"{_id} not found in save file")


class InvalidURL(Exception):
    def __init__(self, _url: str):
        super().__init__(f"{_url} is invalid")


class TaskClass:
    def __init__(
        self,
        group_id: str,
        task_name: str,
        task_id: str | None = None,
        button_text: str | None = None,
        url: str | None = None,
        file_path: str | None = None,
        directory_path: str | None = None,
    ):
        """
        Class to hold all the required details that a task requires.
        Task name should always be provided.
        All other parameters are optional and can be added/updated at a later date.

        :param task_name: Name of task
        :param task_id: unique id Of task (automatically assigned if not given)
        :param button_text: text to show on button
        :param url: string of url, if separated by comma they will be split into string for saving
        :param file_path: filepath string
        :param directory_path: directory path string
        """
        if task_id is None:
            self.task_id = f"T_{id(self)}"
            count = 1
            while is_id_used(self.task_id):
                self.task_id = f"T_{id(self)}-{str(count)}"
                count += 1
        else:
            self.task_id = task_id

        self.group_id = group_id
        self.task_name = task_name
        self.button_text = button_text
        self.url = url
        self.file_path = file_path
        self.directory_path = directory_path

        self.save_task()

    def __str__(self):
        return self.task_name

    def __repr__(self):
        return (
            "TaskClass("
            f"task_id = {self.task_id} "
            f"task_name = {self.task_name} "
            f"url = {self._url}"
            f"file_path = {self.button_text})"
            f"directory_path = {self.directory_path}"
        )

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, new_url: str | None):
        if new_url is None:
            self._url = []
        elif type(new_url) == list:
            self._url = new_url
        else:
            new_url = new_url.replace(",", " ")
            url_list = new_url.split()

            for index, _url in enumerate(url_list):
                if (fixed_url := self.verify_url_root(_url)) is not None:
                    url_list[index] = fixed_url
                else:
                    url_list.pop(index)

            self._url = url_list

    @staticmethod
    def verify_url_root(url_check: str) -> str | None:
        """
        Uses requests to verify the url being opened.
        http will be added if required to ensure default browser is opened
        http vs https will also be checked
        :param url_check: the url to check
        :return: the fixed url or None for error handling
        """
        if "http" not in url_check[:4]:
            url_check = f"http://{url_check}"

        try:
            _req = requests.get(url_check)
        except requests.exceptions.RequestException:
            return None

        if not _req.history:
            return url_check
        return _req.url if _req.history[0].is_redirect else None

    def edit_task(
        self,
        task_name: str,
        button_text: str | None = None,
        url: str | None = None,
        file_path: str | None = None,
        directory_path: str | None = None,
    ):
        """
        Edit any or all variables in the task.

        :param task_name: Name of task
        :param button_text: text to show on button
        :param url: string of url, if separated by comma they will be split into list for saving
        :param file_path: filepath string
        :param directory_path: directory path string
        """
        self.task_name = task_name
        self.button_text = button_text
        self.url = url
        self.file_path = file_path
        self.directory_path = directory_path

        self.save_task()

    def get_task_data(self) -> dict:
        """
        Simple return method to get all data in a dictionary.
        Mainly used for the Save_task method.

        :return: dictionary of all variables
        """
        return {
            "task_name": self.task_name,
            "button_text": self.button_text,
            "url": self.url,
            "file_path": self.file_path,
            "directory_path": self.directory_path,
        }

    def delete_task(self) -> None:
        """
        Will delete the task from the Save_File.
        Does not search for any associated groups so should only be used when deleting the parent group.
        """
        # get group of this task and delete from task to remove it from the group as well
        group = get_group_by_id(self.group_id)
        group.delete_task(self.task_id)

    def save_task(self) -> None:
        """
        Saves task to the Save_file.
        Does not search for any associated groups so should only be used when saving the parent group.
        """
        with open(FILE_PATH, "r") as save_file:
            json_data = json.load(save_file)

        json_data["tasks"].update({self.task_id: self.get_task_data()})

        with open(FILE_PATH, "w") as save_file:
            json.dump(json_data, save_file, indent=4)


class GroupClass:
    def __init__(
        self,
        group_name: str,
        group_id: str | None = None,
        group_tasks: list[str] | None = None,
    ):
        """
        Class to hold all the required details that a group requires.
        Group name should always be provided.
        All other parameters are optional and can be added/updated at a later date.

        GroupClass can be treated as an iterable. Using in such a way will access the group_task list for easy addition
        or removal of tasks to the group.

        :param group_name: logical name for the group
        :param group_id: auto-generated id if not provided
        :param group_tasks: list of associated task ids
        """
        if group_id is None:
            self.group_id = f"G_{id(self)}"
            count = 1
            while is_id_used(self.group_id):
                self.group_id = f"G_{id(self)}-{str(count)}"
                count += 1
        else:
            self.group_id = group_id

        self._group_name = group_name

        if group_tasks is None or not group_tasks:
            self.group_tasks = []
        else:
            self.group_tasks = group_tasks

        self.save_group()

    def __iter__(self):
        self.i = 0
        return self

    def __next__(self):
        if self.group_tasks is None:
            raise NoTasks(self.group_name)
        if self.i < (len(self.group_tasks) - 1):
            task_id = self.group_tasks[self.i]
            self.i += 1
            return task_id
        raise StopIteration

    def __str__(self):
        return self.group_name

    def __repr__(self):
        return (
            "GroupClass("
            f"group_id = {self.group_id} "
            f"group_name = {self.group_name} "
            f"group_tasks = {self.group_tasks})"
        )

    @property
    def group_name(self):
        """
        Get or set the current group name.
        Setting the group name will auto-save the update to the savefile.
        """
        return self._group_name

    @group_name.setter
    def group_name(self, new_group_name: str):
        self._group_name = new_group_name
        self.save_group()

    def delete_group_and_tasks(self):
        """
        Will delete the group and all associated tasks from the SaveFile.
        The method will loop through 'group_tasks' to delete all tasks
        individually.
        """
        with open(FILE_PATH, "r") as save_file:
            json_data = json.load(save_file)

        json_data["groups"].pop(str(self.group_id))

        with open(FILE_PATH, "w") as save_file:
            json.dump(json_data, save_file, indent=4)

        for task in self.group_tasks:
            get_task_by_id(task).delete_task()

    def insert(self, index, new_task_id: str) -> None:
        """
        Inserts the given task into the list of tasks at index.
        Will raise TaskAlreadyInGroup error to avoid duplicates.

        :param index: index location in list
        :param new_task_id: id of new task to be added
        """
        if new_task_id in self.group_tasks:
            raise TaskAlreadyInGroup(self.group_name, new_task_id)
        self.group_tasks.insert(index, new_task_id)
        self.save_group()

    def append(self, new_task_id: str) -> None:
        """
        appends the given task into the list.
        Will raise TaskAlreadyInGroup error to avoid duplicates.

        :param new_task_id: id of new task to be added
        """
        if new_task_id in self.group_tasks:
            raise TaskAlreadyInGroup(self.group_name, new_task_id)
        self.group_tasks.append(new_task_id)
        self.save_group()

    def remove(self, task_id: str) -> None:
        """
        removes the given task into the list.
        Will raise TaskNotFoundInGroup if the task was not in the group already.

        :param task_id: id of new task to be removed
        """
        if task_id not in self.group_tasks:
            raise TaskNotFoundInGroup(self.group_name, task_id)
        self.group_tasks.remove(task_id)
        self.save_group()

    def create_task(
        self,
        task_name: str,
        task_id: str | None = None,
        button_text: str | None = None,
        url: str | None = None,
        file_path: str | None = None,
        directory_path: str | None = None,
    ) -> TaskClass:
        """
        Create a task from within the group_class space. All parameters are the same as would be when creating a
        standalone task. This method also appends the task_id to the group_task list.

        :param task_name: Name of task
        :param task_id: unique id Of task (automatically assigned if not given)
        :param button_text: text to show on button
        :param url: string of url, if separated by comma they will be split into string for saving
        :param file_path: filepath string
        :param directory_path: directory path string
        """
        new_task = TaskClass(self.group_id, task_name, task_id, button_text, url, file_path, directory_path)

        self.group_tasks.append(new_task.task_id)
        self.save_group()

        return new_task

    def delete_task(self, task_id: str) -> None:
        """
        Will delete the given task from the save_file and remove it from the
        group_tasks list.

        :param task_id: id of the task to be deleted
        """
        if task_id not in self.group_tasks:
            raise TaskNotFoundInGroup(self.group_name, task_id)
        self.remove(task_id)
        delete_task_by_id(task_id)

    def get_tasks(self) -> list[TaskClass]:
        """
        Returns a list of objects of all the tasks associated with the
        GroupClass.

        :return: list of TaskClass object
        """
        return [get_task_by_id(str(task)) for task in self.group_tasks]

    def delete_group(self) -> None:
        delete_group_by_id(self.group_id)

    def save_group(self) -> None:
        """
        Saves the group to the SaveFile
        """
        with open(FILE_PATH, "r") as save_file:
            json_data = json.load(save_file)

        json_data["groups"].update(
            {
                str(self.group_id): {
                    "group_name": self.group_name,
                    "group_tasks": self.group_tasks,
                }
            }
        )

        with open(FILE_PATH, "w") as save_file:
            json.dump(json_data, save_file, indent=4)


def get_task_by_id(task_id: str) -> TaskClass:
    """
    Used to get and create a TaskClass object from its id and the SaveFile.
    Mainly used to reconstruct tasks during startup
    from the parent group.

    :param task_id: id of the task to be returned from the SaveFile
    :return: TaskClass object
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    if task_id not in [str(i) for i in json_data["tasks"]]:
        raise NotFoundInFile(task_id)

    task_data = json_data["tasks"][f"{task_id}"]

    return TaskClass(
        group_id=get_group_id_of_task(task_id),
        task_name=task_data["task_name"],
        task_id=task_id,
        button_text=task_data["button_text"],
        url=task_data["url"],
        file_path=task_data["file_path"],
        directory_path=task_data["directory_path"],
    )



def get_group_by_id(group_id: str) -> GroupClass:
    """
    Used to get and create a GroupClass object from its id and the SaveFile.

    :param group_id: id of the group to be returned from the SaveFile
    :return: GroupClass object
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    group_data = json_data["groups"][f"{group_id}"]

    return GroupClass(
        group_name=group_data["group_name"],
        group_id=group_id,
        group_tasks=list(group_data["group_tasks"]),
    )


def delete_task_by_id(task_id: str) -> None:
    """
    Delete a task from the SaveFile by using its id as a lookup.
    :param task_id: id of the task to be deleted.
    """
    get_task_by_id(task_id).delete_task()


def get_group_id_of_task(task_id: str) -> str:
    """Returns the group_id of the given task_id."""
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)
        groups: dict[str, dict] = json_data["groups"]

    for group_id, group in groups.items():
        if task_id in group["group_tasks"]:
            return group_id
    raise NotFound(f"Task with id '{task_id}' not found in any groups.")


def delete_group_by_id(group_id: str) -> None:
    """
    Delete a group and its tasks from the SaveFile by using its id as a lookup.
    :param group_id: id of the group to be deleted.
    """
    get_group_by_id(group_id).delete_group_and_tasks()


def is_id_used(_id: str | int) -> bool:
    """
    A check on whether an id exists already in the SaveFile.
    :param _id: id to be checked
    :return: returns a bool True if the id is in use already
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)
    return _id in json_data["groups"] or _id in json_data["tasks"]


def load_groups() -> list[str]:
    """
    loads a list of group ids currently in the SaveFile.
    :return: list of ids as strings
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    return list(json_data["groups"])


def reorder_groups(new_order: list) -> None:
    """
    Will reorder the groups in the save file to the new order list.
    :param new_order: List of group ids for the new order
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    original_groups_dict = json_data["groups"]

    json_data["groups"] = {k: original_groups_dict[k] for k in new_order}

    with open(FILE_PATH, "w") as save_file:
        json.dump(json_data, save_file, indent=4)


def reorder_items(new_order: list) -> None:
    """
    Will reorder the items in the save file to the new order list.
    :param new_order: List of item ids for the new order
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    original_items_dict = json_data["items"]

    json_data["items"] = {k: original_items_dict[k] for k in new_order}

    with open(FILE_PATH, "w") as save_file:
        json.dump(json_data, save_file, indent=4)


def load_tasks() -> list:
    """
    loads a list of task ids currently in the SaveFile.
    :return: list of ids as strings
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    return list(json_data["tasks"])


def apply_settings(name: str, value=None) -> None:
    """
    apply the given settings to the name key in the 'settings' dictionary within the SaveFile.
    :param name: key name for the setting to be applied
    :param value: value for the setting to be applied
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    json_data["settings"].update({name: value})

    with open(FILE_PATH, "w") as save_file:
        json.dump(json_data, save_file, indent=4)


def get_setting(name: str) -> dict:
    """
    Retrieves the key value dictionary for the given key from the 'settings' dictionary within the SaveFile.
    :param name: key for dictionary to be returned
    :return: dictionary with key given and value found
    """
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)["settings"]

    if name in json_data:
        return json_data[name]
    raise NotFound(name)


def remove_setting(name: str) -> None:
    with open(FILE_PATH, "r") as save_file:
        json_data = json.load(save_file)

    if name in json_data["settings"]:
        del json_data["settings"][name]
        with open(FILE_PATH, "w") as save_file:
            json.dump(json_data, save_file, indent=4)

    raise NotFound(name)
