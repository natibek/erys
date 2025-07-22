from typing import Any
from jupyter_client import KernelManager, BlockingKernelClient
from threading import Lock
import os


class NotebookKernel:
    """Class for kernel for each notebook. Contains kernel manager and client used to
    execute code.
    """

    def __init__(self) -> None:
        # lock to prevent data races when calling `run_code` for multiple cells asynchronously
        self.execution_lock = Lock()
        self.initialized = False

    def initialize(self) -> None:
        """Initializes the notebook kernel's kernel manager and kernel client."""

        try:
            self.kernel_manager: KernelManager = KernelManager()  # kernel manager
            import ipykernel
            ipykernel_path = os.path.join(os.path.dirname(ipykernel.__file__), "ipykernel_launcher.py")
            self.kernel_manager.kernel_cmd = [ipykernel_path, "-f", "{connection_file}"]

            self.kernel_manager.start_kernel()
            try:
                self.kernel_client: BlockingKernelClient = (
                    self.kernel_manager.client()
                )  # kernel client
                self.kernel_client.start_channels()
            except:
                self.kernel_manager.shutdown_kernel()
                self.initialized = False
                return
        except:
            self.initialized = False
            return

        self.initialized = True

    def get_kernel_info(self) -> dict[str, str]:
        """Get the kernel info for the notebook metadata.

        Returns: the dictionary representing the kernel info.
        """
        return {"name": self.kernel_manager.kernel_name}

    def get_kernel_spec(self) -> dict[str, str]:
        """Get the kernel spec for the notebook metadata.

        Returns: the dictionary representing the kernel spec.
        """
        try:
            spec = self.kernel_manager.kernel_spec
            return {
                "display_name": spec.display_name,
                "language": spec.lanugage,
                "name": spec.name,
            }
        except:
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
