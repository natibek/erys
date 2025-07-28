# Copyright 2025 Nathnael (Nati) Bekele
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Any
from jupyter_client import KernelManager, BlockingKernelClient, kernelspec
import uuid
import subprocess
import json
import os
import shutil
from pathlib import Path

ERYS_KERNEL_NAME = "erys_kernel_"
ERYS_DISPLAY_NAME = "erys_kernel"


class NotebookKernel:
    """Class for a kernel for each notebook. Contains kernel manager and client used to
    execute code.
    """

    def __init__(self) -> None:
        self.ksm = kernelspec.KernelSpecManager()
        self.venv_path = os.getenv("VIRTUAL_ENV") or os.getenv("CONDA_PREFIX")
        self.in_venv = self.venv_path is not None
        self.kernel_client: BlockingKernelClient = None
        self.kernel_manager: KernelManager = None

        if self.in_venv:
            if self._check_for_ipykernel():
                # only attempt to connect to the kernel if ipykernel is installed
                self.kernel_path = Path(self.venv_path).joinpath("share/jupyter/")
                os.environ["JUPYTER_PATH"] = str(self.kernel_path)
                self.initialized = True
                self.initialize()
            else:
                self.initialized = False
        else:
            self.initialized = False

    @property
    def display_name(self) -> str:
        """Return the kernel name."""
        try:
            return self.kernel_manager.kernel_spec.display_name
        except:
            return ""

    def initialize(self) -> None:
        """Initializes the notebook kernel's kernel manager and kernel client.
        If kernel specs made by `Erys` are found, they are prioritized.
        """

        kernel_spec, kernel_name = self._get_target_kernel_spec()

        if not kernel_spec:
            kernel_spec, kernel_name = self._create_new_kernel_spec()

        self.connect_to_kernel(kernel_spec, kernel_name)

    def connect_to_kernel_by_name(self, kernel_name: str) -> None:
        """Connect with a kernel with the given name and start a `BlockingKernelClient`
        to use for code executation.

        Args:
            kernel_name: name of the kernel to connect to.
        """
        self.shutdown_kernel()  # will shutdown existing client channels and kernel manager

        kernel_spec = self._get_target_kernel_spec(kernel_name=kernel_name)

        if kernel_spec:
            self.connect_to_kernel(kernel_spec, kernel_name)

    def connect_to_kernel(self, kernel_spec: dict[str, Any], kernel_name) -> None:
        """Connect with a kernel defined by the given kernel spec nad kernel name.
        Then start a `BlockingKernelClient` to use for code execution.

        Args:
            kernel_spec: spec for the kernel to connect to.
            kernel_name: name of the kernel
        """
        self.shutdown_kernel()  # will shutdown existing client channels and kernel manager
        self.kernel_manager: KernelManager = KernelManager(
            kernel_name=kernel_name
        )  # kernel manager

        # need to manually provide kernel command so that it is not over ridden by
        # implementation
        self.kernel_manager.kernel_cmd = kernel_spec["argv"]
        self.kernel_manager.kernel_spec.argv = kernel_spec["argv"]
        self.kernel_manager.kernel_spec.language = kernel_spec["language"]
        self.kernel_manager.kernel_spec.display_name = kernel_spec["display_name"]
        self.kernel_manager.kernel_spec.env = kernel_spec["env"]
        self.kernel_manager.kernel_spec.interrupt_mode = kernel_spec["interrupt_mode"]
        self.kernel_manager.kernel_spec.metadata = kernel_spec["metadata"]

        self.kernel_manager.start_kernel()

        self.kernel_client: BlockingKernelClient = (
            self.kernel_manager.client()
        )  # kernel client
        self.kernel_client.start_channels()

    def _create_new_kernel_spec(self) -> tuple[dict[str, Any], str]:
        """Creates new kernel spec in the current python environment.

        Returns the kernel spec and kernel name.
        """
        kernel_name = ERYS_KERNEL_NAME + self._generate_id()
        kernel_spec = self._install_custom_kernel(
            kernel_name=kernel_name,
            display_name=ERYS_DISPLAY_NAME,
        )
        return kernel_spec, kernel_name

    def _generate_id(self) -> str:
        """Generate unique id to use in kernel names created by Erys to avoid collision.

        Returns a uuid hex.
        """
        return uuid.uuid4().hex[:5]

    def _install_custom_kernel(
        self, kernel_name: str, display_name: str
    ) -> dict[str, Any]:
        """Writes the kernel specs for a custom `erys` kernel to the virtual enrivonments
        jupyter path.

        Returns the created kernel spec.
        """
        spec_path = self.kernel_path.joinpath(f"kernels/{kernel_name}")
        argv = [
            str(Path(self.venv_path).joinpath("bin/python")),
            "-Xfrozen_modules=off",
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ]

        kernel_spec = {
            "argv": argv,
            "env": {},
            "display_name": display_name,
            "language": "python",
            "interrupt_mode": "signal",
            "metadata": {"debugger": True},
        }

        spec_path.mkdir(parents=True, exist_ok=True)
        with open(spec_path.joinpath("kernel.json"), "w") as spec_file:
            json.dump(kernel_spec, spec_file)

        return kernel_spec

    def _check_for_ipykernel(self) -> bool:
        """Check if the virtual enrivonment has `ipykernel` installed.

        Returns: whether `ipykernel` is installed in environment.
        """

        executable = str(Path(self.venv_path).joinpath("bin/python"))
        cmd = [
            executable,
            "-c",
            "import importlib.util; print(importlib.util.find_spec('ipykernel') is not None)",
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=True,
        )
        return eval(result.stdout)

    def _get_available_kernels(self) -> dict[str, str]:
        """Find all the available kernels in the current environment.

        Retuns a dictionary with kernel name as key and resource dir as value.
        """
        return self.ksm.get_all_specs()

    def _update_kernel_cmd(self, kernel_spec: dict[str, Any]) -> dict[str, Any]:
        """Expands the relative python executable path in the kernel cmd of a kernel sepc
        to include path to the environment and disables frozen modules.

        Args:
            kernel_spec: the spec to expand executable path for and disable frozen modules.

        Returns kernel spec.
        """
        kernel_cmd: list[str] = kernel_spec["argv"]
        if kernel_cmd[0] in ["python", "python2", "python3"]:
            kernel_cmd[0] = shutil.which(kernel_cmd[0])

        if "-Xfrozen_modules=off" not in kernel_cmd:
            kernel_cmd.insert(1, "-Xfrozen_modules=off")

        return kernel_spec

    def _get_target_kernel_spec(
        self, kernel_name: str | None = None
    ) -> tuple[dict[str, Any], str]:
        """Goes through all the kernel specs and finds the for the kernel in the current python
        environment and check if it has the provided kernel name if any is.

        Returns: the kernel spec and kernel name.
        """
        kernel_specs = self._get_available_kernels()

        if not kernel_specs:
            return {}, ""

        target_kernel_spec = {}
        target_kernel_name = ""
        for name, spec in kernel_specs.items():
            resource_dir = spec["resource_dir"]
            if Path(resource_dir).is_relative_to(self.venv_path):
                target_kernel_spec = spec["spec"]
                target_kernel_name = name

                if kernel_name and name == kernel_name:
                    break
                elif kernel_name is None and name.startswith(ERYS_KERNEL_NAME):
                    break

        if target_kernel_spec:
            target_kernel_spec = self._update_kernel_cmd(target_kernel_spec)

        return target_kernel_spec, target_kernel_name

    def get_kernel_info(self) -> dict[str, str]:
        """Get the kernel info for the notebook metadata.

        Returns: the dictionary representing the kernel info.
        """
        return {"name": self.kernel_manager.kernel_name}

    def get_kernel_spec(self) -> dict[str, str]:
        """Get the kernel spec for the notebook metadata.

        Returns: the dictionary representing the kernel spec.
        """
        spec = self.kernel_manager.kernel_spec
        if spec:
            return {
                "display_name": spec.display_name,
                "language": spec.language,
                "name": spec.name,
            }

        return {
            "display_name": "",
            "language": "",
            "name": "",
        }

    def get_language_info(self) -> dict[str, Any]:
        """Get the language info for the notebook metadata.

        Returns: the dictionary representing the language info.
        """
        language_info = {}
        try:
            self.kernel_client.kernel_info()
            msg = self.kernel_client.get_shell_msg(timeout=5)

            if msg["header"]["msg_type"] == "kernel_info_reply":
                language_info = msg["content"].get("language_info", {})
        finally:
            return language_info

    def run_code(self, code: str) -> list[dict[str, Any]]:
        """Run provided code string with the kernel. Uses the iopub channel to get results.

        Args:
            code: code string.

        Returns: the outputs of executing the code with the kernel.
        """
        if not self.initialized:
            return None

        self.kernel_client.execute(code)

        # Read the output from the iopub channel
        outputs = []
        execution_count = None
        while True:
            try:
                msg = self.kernel_client.get_iopub_msg()
                msg_type = msg["header"]["msg_type"]
                match msg_type:
                    case "status":
                        if msg["content"]["execution_state"] == "idle":
                            break
                    case "execute_input":
                        # if no execute output is present for execution, execution count can
                        # be found from the execute_input output
                        execution_count = msg["content"]["execution_count"]
                    case "display_data" | "stream" | "error" | "execute_result":
                        output = msg["content"]
                        output["output_type"] = msg_type
                        outputs.append(output)
            except Exception:
                pass
        return outputs, execution_count

    def interrupt_kernel(self) -> None:
        """Interrupt the kernel."""
        if not self.initialized:
            return None
        self.kernel_manager.interrupt_kernel()

    def restart_kernel(self) -> None:
        """Restart the kernel."""
        if not self.initialized:
            return None

        self.kernel_client.stop_channels()
        self.kernel_manager.restart_kernel()
        self.kernel_client: BlockingKernelClient = self.kernel_manager.client()
        self.kernel_client.start_channels()

    def shutdown_kernel(self) -> None:
        """Shutdown the kernel."""
        if self.kernel_client:
            self.kernel_client.stop_channels()

        if self.kernel_manager:
            self.kernel_manager.shutdown_kernel()


if __name__ == "__main__":
    nk = NotebookKernel()
    print(nk.get_kernel_spec())
    print(nk.get_language_info())
    print(nk.get_kernel_info())
