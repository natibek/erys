from typing import Any
from jupyter_client import KernelManager, BlockingKernelClient, kernelspec
from ipykernel.kernelspec import install
import uuid
import sys
import os
from pathlib import Path

ERYS_KERNEL_NAME = "erys_kernel_"
ERYS_DISPLAY_NAME = "erys_kernel"

class NotebookKernel:
    """Class for kernel for each notebook. Contains kernel manager and client used to
    execute code.
    """

    def __init__(self) -> None:
        # lock to prevent data races when calling `run_code` for multiple cells asynchronously
        self.ksm = kernelspec.KernelSpecManager()
        self.venv = os.getenv("VIRTUAL_ENV")
        if self.venv is None:
            self.initialized = False
        else:
            self.initialize()
            self.initialized = True

    def initialize(self) -> True:
        """Initializes the notebook kernel's kernel manager and kernel client."""

            # install(user=True, kernel_name="erys_env_kernel")
        start_cmd = self.get_kernel_start_cmd() 
        if start_cmd == "":
            kernel_name = ERYS_KERNEL_NAME + self._generate_id()
            install(
                user=True,
                kernel_name=kernel_name,
                display_name=ERYS_DISPLAY_NAME,
                prefix=sys.prefix
            )
            kernel_specs = self.ksm.get_all_specs()
            start_cmd = kernel_specs[kernel_name]["spec"]["argv"]

        self.kernel_manager: KernelManager = KernelManager()  # kernel manager
        self.kernel_manager.kernel_cmd = start_cmd

        self.kernel_manager.start_kernel()
        self.kernel_client: BlockingKernelClient = (
            self.kernel_manager.client()
        )  # kernel client
        self.kernel_client.start_channels()

    def _generate_id(self) -> str:
        """Generate unique id to use in kernel names created by Erys to avoid collision.

        Returns a uuid hex. 
        """
        return uuid.uuid4().hex[:5]

    def get_kernel_start_cmd(self) -> list[str]:
        """Goes through all the kernel specs and finds the for the kernel in the current Python
        environment to return the start command that will be used by the `KernelManager` to
        start the correct kernel. If no kernel specs are found or the kernels don't belong to
        the current Python environment, returns an empty list.

        Returns: the start command to start kernel belonging to the current Python environment.
        """
        kernel_specs = self.ksm.get_all_specs()

        if not kernel_specs: return []

        sys_prefix = sys.prefix

        start_cmd = []
        for kernel_name, spec in kernel_specs.items():
            resource_dir = spec["resource_dir"]
            if Path(resource_dir).is_relative_to(sys_prefix):
                start_cmd = spec["spec"]["argv"]
                # if a erys created kernel is found, exit early
                if kernel_name.startswith(ERYS_KERNEL_NAME): 
                    return start_cmd
        
        return start_cmd


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
        return {
            "display_name": spec.display_name,
            "language": spec.lanugage,
            "name": spec.name,
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
        self.kernel_client.execute(code)

        # Read the output from the iopub channel
        outputs = []
        execution_count = None
        while True:
            try:
                msg = self.kernel_client.get_iopub_msg()
                match msg["header"]["msg_type"]:
                    case "execute_input":
                        # if no execute output is present for execution, execution count can
                        # be found from the execute_input output
                        execution_count = msg["content"]["execution_count"]
                    case "display_data":
                        # {
                        #    "output_type": "display_data",
                        #    "data": {
                        #        "text/plain": "[multiline text data]",
                        #        "image/png": "[base64-encoded-multiline-png-data]",
                        #        "application/json": {
                        #            # JSON data is included as-is
                        #            "key1": "data",
                        #            "key2": ["some", "values"],
                        #            "key3": {"more": "data"},
                        #        },
                        #        "application/vnd.exampleorg.type+json": {
                        #            # JSON data, included as-is, when the mime-type key ends in +json
                        #            "key1": "data",
                        #            "key2": ["some", "values"],
                        #            "key3": {"more": "data"},
                        #        },
                        #    },
                        #    "metadata": {
                        #        "image/png": {
                        #            "width": 640,
                        #            "height": 480,
                        #        },
                        #    },
                        # }
                        output = msg["content"]
                        output["output_type"] = "display_data"
                        outputs.append(output)
                    case "stream":
                        # {
                        #   "output_type" : "stream",
                        #   "name" : "stdout", # or stderr
                        #   "text" : ["multiline stream text"],
                        # }
                        output = msg["content"]
                        output["output_type"] = "stream"
                        outputs.append(output)
                    case "error":
                        # {
                        #   'ename' : str,   # Exception name, as a string
                        #   'evalue' : str,  # Exception value, as a string
                        #   'traceback' : list,
                        # }
                        output = msg["content"]
                        output["output_type"] = "error"
                        outputs.append(output)
                    case "execute_result":
                        # {
                        #   "output_type" : "execute_result",
                        #   "execution_count": 42,
                        #   "data" : {
                        #     "text/plain" : ["multiline text data"],
                        #     "image/png": ["base64-encoded-png-data"],
                        #     "application/json": {
                        #       # JSON data is included as-is
                        #       "json": "data",
                        #     },
                        #   },
                        #   "metadata" : {
                        #     "image/png": {
                        #       "width": 640,
                        #       "height": 480,
                        #     },
                        #   },
                        # }
                        output = msg["content"]
                        output["output_type"] = "execute_result"
                        outputs.append(output)
                    case "status":
                        if msg["content"]["execution_state"] == "idle":
                            break
            except Exception as e:
                pass
        return outputs, execution_count

    def interrupt_kernel(self) -> None:
        """Interrupt the kernel."""
        self.kernel_manager.interrupt_kernel()

    def restart_kernel(self) -> None:
        """Restart the kernel."""
        self.kernel_client.stop_channels()
        self.kernel_manager.restart_kernel()
        self.kernel_client: BlockingKernelClient = self.kernel_manager.client()
        self.kernel_client.start_channels()

    def shutdown_kernel(self) -> None:
        """Shutdown the kernel."""
        self.kernel_client.stop_channels()
        self.kernel_manager.shutdown_kernel()
