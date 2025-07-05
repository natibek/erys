from typing import Any
from jupyter_client import KernelManager, BlockingKernelClient


class NotebookKernel:
    def __init__(self) -> None:
        self.kernel_manager: KernelManager = KernelManager()
        self.kernel_manager.start_kernel()

        self.kernel_manager.kernel_name
        self.kernel_client: BlockingKernelClient = self.kernel_manager.client()
        self.kernel_client.start_channels()

    def get_kernel_info(self):
        return {"name": self.kernel_manager.kernel_name}

    def get_kernel_spec(self):
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

    def get_language_info(self):
        language_info = {}
        try:
            self.kernel_client.kernel_info()
            msg = self.kernel_client.get_shell_msg(timeout=5)

            if msg["header"]["msg_type"] == "kernel_info_reply":
                language_info = msg["content"].get("language_info", {})
        finally:
            return language_info

    def run_code(self, code: str) -> list[dict[str, Any]]:
        self.kernel_client.wait_for_ready(timeout=5)
        self.kernel_client.execute(code)

        # Read the output
        outputs = []
        execution_count = None
        while True:
            try:
                msg = self.kernel_client.get_iopub_msg()
                match msg["header"]["msg_type"]:
                    case "execute_input":
                        execution_count = msg["content"]["execution_count"]
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

    def restart_kernel(self) -> None:
        self.kernel_client.stop_channels()
        self.kernel_manager.restart_kernel(now=True)
        self.kernel_manager.start_kernel()

    def shutdown_kernel(self) -> None:
        self.kernel_client.stop_channels()
        self.kernel_manager.shutdown_kernel(now=True)
