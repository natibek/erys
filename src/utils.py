import uuid

DOUBLE_CLICK_INTERVAL = 0.4  # seconds
COLLAPSED_COLOR = "green"
EXPANDED_COLOR = "white"


# https://github.com/jupyter/enhancement-proposals/blob/master/62-cell-id/cell-id.md
def get_cell_id(id_length=8):
    return uuid.uuid4().hex[:id_length]
