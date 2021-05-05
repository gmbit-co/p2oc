import os
import sys

# HACK: Workaround for relative import in protobuf under python3
# https://github.com/PaddlePaddle/Paddle/pull/18239
cur_path = os.path.dirname(__file__)
parent_path = os.path.dirname(cur_path)
sys.path.append(os.path.join(parent_path, "lnrpc"))
