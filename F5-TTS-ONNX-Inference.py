# data entry start

import customtkinter as cstk
from customtkinter import StringVar
import json
import os

# save-load start
config_file = "config.json"

def load_config():
    if os.path.exists(config_file):
        with open(config_file, "r") as file:
            return json.load(file)
    return {}

def save_config():
    config = {
        "gentxt": gentxt.get(),
        "vocpath": vocpath.get(),
        "oma": oma.get(),
        "omb": omb.get(),
        "omc": omc.get(),
        "refa": refa.get(),
        "gena": gena.get(),
        "reftxt": reftxt.get(),
    }
    with open(config_file, "w") as file:
        json.dump(config, file, indent=4)

config = load_config()
# save-load end

cstk.set_appearance_mode("dark")
cstk.set_default_color_theme("dark-blue")

root = cstk.CTk()
root.title('F5-TTS-ONNX GUI')
root.geometry("540x440")
root.configure(bg = "#664848")
root.resizable(width=False, height=False)

gentxt = StringVar(root, config.get("gentxt", "write what you want generated"))
vocpath = StringVar(root, config.get("vocpath", "./models"))
oma = StringVar(root, config.get("oma", "./models/onnx/F5_Preprocess.onnx"))
omb = StringVar(root, config.get("omb", "./models/onnx/F5_Transformer.onnx"))
omc = StringVar(root, config.get("omc", "./models/onnx/F5_Decode.onnx"))
refa = StringVar(root, config.get("refa", "./audio/sample.wav"))
gena = StringVar(root, config.get("gena", "./audio/generated/generated_audio.wav"))
reftxt = StringVar(root, config.get("reftxt", "And now, coming to you from the classiest station on the air, this is "))

label = cstk.CTkLabel(master=root, text="F5-TTS-ONNX GUI", font=("Roboto", 16))
label.grid(row=0, column=0, padx=10, pady=10)

label2 = cstk.CTkLabel(master=root, text="Text you want to be generated with the sample's voice :", font=("Roboto", 12), compound="left", justify="left", anchor="w")
label2.grid(row=1, column=0, padx=10, pady=1,sticky="w")     
        
igentxt = cstk.CTkEntry(root,width=600,height=16, textvariable = gentxt)
igentxt.grid(row=2, column=0, padx=10, pady=1)

label2 = cstk.CTkLabel(master=root, text="Vocab file path and name (Only needed if you change the language) :", font=("Roboto", 12), compound="left", justify="left", anchor="w")
label2.grid(row=3, column=0, padx=10, pady=1,sticky="w")     
        
ivocpath = cstk.CTkEntry(root,width=600,height=16, textvariable = vocpath)
ivocpath.grid(row=4, column=0, padx=10, pady=1)

label2 = cstk.CTkLabel(master=root, text="Change these three if you use a different model :", font=("Roboto", 12), compound="left", justify="left", anchor="w")
label2.grid(row=5, column=0, padx=10, pady=1,sticky="w") 
       
ioma = cstk.CTkEntry(root,width=600,height=16, textvariable = oma)
ioma.grid(row=6, column=0, padx=10, pady=1)
        
iomb = cstk.CTkEntry(root,width=600,height=16, textvariable = omb)
iomb.grid(row=7, column=0, padx=10, pady=1)
       
iomc = cstk.CTkEntry(root,width=600,height=16, textvariable = omc)
iomc.grid(row=8, column=0, padx=10, pady=1)

label2 = cstk.CTkLabel(master=root, text="Reference Audio File Name (can be wav or mp3, MUST BE MONO) :", font=("Roboto", 12), compound="left", justify="left", anchor="w")
label2.grid(row=9, column=0, padx=10, pady=1,sticky="w") 
        
irefa = cstk.CTkEntry(root,width=600,height=16, textvariable = refa)
irefa.grid(row=10, column=0, padx=10, pady=1)

label2 = cstk.CTkLabel(master=root, text="Generated Audio File Name (extension can be wav or mp3) :", font=("Roboto", 12))
label2.grid(row=11, column=0, padx=10, pady=1,sticky="w") 
               
igena = cstk.CTkEntry(root,width=600,height=16, textvariable = gena)
igena.grid(row=12, column=0, padx=10, pady=1)

label = cstk.CTkLabel(master=root, text="Reference Text (change only if you use different reference audio) :", font=("Roboto", 12), compound="left", justify="left", anchor="w")
label.grid(row=13, column=0, padx=10, pady=1,sticky="w")   
        
ireftxt = cstk.CTkEntry(root,width=600,height=32, textvariable = reftxt)
ireftxt.grid(row=14, column=0, padx=10, pady=5)
    
cstk.CTkButton(root, text="SAVE & EXECUTE", width=160, command=lambda: [save_config(), root.destroy()]).grid(row=10, column=0)
   
root.mainloop()
#data entry end

import re
import sys
import time
import jieba
import numpy as np
import onnxruntime
import torch
import torchaudio
from pypinyin import lazy_pinyin, Style

gen_text             = gentxt.get()
F5_project_path      = vocpath.get()
onnx_model_A         = oma.get()
onnx_model_B         = omb.get()
onnx_model_C         = omc.get()
reference_audio      = refa.get()
generated_audio      = gena.get()
ref_text             = reftxt.get()
voc_path             = vocpath.get()

ORT_Accelerate_Providers = []           # If you have accelerate devices for : ['CUDAExecutionProvider', 'TensorrtExecutionProvider', 'CoreMLExecutionProvider', 'DmlExecutionProvider', 'OpenVINOExecutionProvider', 'ROCMExecutionProvider', 'MIGraphXExecutionProvider', 'AzureExecutionProvider']
                                        # else keep empty.
HOP_LENGTH = 256                        # Number of samples between successive frames in the STFT
SAMPLE_RATE = 24000                     # The generated audio sample rate
RANDOM_SEED = 9527                      # Set seed to reproduce the generated audio
NFE_STEP = 32                           # F5-TTS model setting
dynamic_axes=False                      # Set True to be able to change speed
SPEED = 1.0                             # Set for talking speed. Only works with dynamic_axes=True


with open(f"{voc_path}/vocab.txt", "r", encoding="utf-8") as f:
    vocab_char_map = {}
    for i, char in enumerate(f):
        vocab_char_map[char[:-1]] = i
vocab_size = len(vocab_char_map)


def is_chinese_char(c):
    cp = ord(c)
    return (
        0x4E00 <= cp <= 0x9FFF or    # CJK Unified Ideographs
        0x3400 <= cp <= 0x4DBF or    # CJK Unified Ideographs Extension A
        0x20000 <= cp <= 0x2A6DF or  # CJK Unified Ideographs Extension B
        0x2A700 <= cp <= 0x2B73F or  # CJK Unified Ideographs Extension C
        0x2B740 <= cp <= 0x2B81F or  # CJK Unified Ideographs Extension D
        0x2B820 <= cp <= 0x2CEAF or  # CJK Unified Ideographs Extension E
        0xF900 <= cp <= 0xFAFF or    # CJK Compatibility Ideographs
        0x2F800 <= cp <= 0x2FA1F     # CJK Compatibility Ideographs Supplement
    )


def convert_char_to_pinyin(text_list, polyphone=True):
    final_text_list = []
    merged_trans = str.maketrans({
        '“': '"', '”': '"', '‘': "'", '’': "'",
        ';': ','
    })
    chinese_punctuations = set("。，、；：？！《》【】—…")
    for text in text_list:
        char_list = []
        text = text.translate(merged_trans)
        for seg in jieba.cut(text):
            if seg.isascii():
                if char_list and len(seg) > 1 and char_list[-1] not in " :'\"":
                    char_list.append(" ")
                char_list.extend(seg)
            elif polyphone and all(is_chinese_char(c) for c in seg):
                pinyin_list = lazy_pinyin(seg, style=Style.TONE3, tone_sandhi=True)
                for c in pinyin_list:
                    if c not in chinese_punctuations:
                        char_list.append(" ")
                    char_list.append(c)
            else:
                for c in seg:
                    if c.isascii():
                        char_list.append(c)
                    elif c in chinese_punctuations:
                        char_list.append(c)
                    else:
                        char_list.append(" ")
                        pinyin = lazy_pinyin(c, style=Style.TONE3, tone_sandhi=True)
                        char_list.extend(pinyin)
        final_text_list.append(char_list)
    return final_text_list


def list_str_to_idx(
    text: list[str] | list[list[str]],
    vocab_char_map: dict[str, int],  # {char: idx}
    padding_value=-1
):
    get_idx = vocab_char_map.get
    list_idx_tensors = [torch.tensor([get_idx(c, 0) for c in t], dtype=torch.int32) for t in text]
    text = torch.nn.utils.rnn.pad_sequence(list_idx_tensors, padding_value=padding_value, batch_first=True)
    return text


# ONNX Runtime settings
onnxruntime.set_seed(RANDOM_SEED)
session_opts = onnxruntime.SessionOptions()
session_opts.log_severity_level = 3  # error level, it a adjustable value.
session_opts.inter_op_num_threads = 0  # Run different nodes with num_threads. Set 0 for auto.
session_opts.intra_op_num_threads = 0  # Under the node, execute the operators with num_threads. Set 0 for auto.
session_opts.enable_cpu_mem_arena = True  # True for execute speed; False for less memory usage.
session_opts.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
session_opts.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
session_opts.add_session_config_entry("session.intra_op.allow_spinning", "1")
session_opts.add_session_config_entry("session.inter_op.allow_spinning", "1")


ort_session_A = onnxruntime.InferenceSession(onnx_model_A, sess_options=session_opts, providers=['CPUExecutionProvider'])
model_type = ort_session_A._inputs_meta[0].type
in_name_A = ort_session_A.get_inputs()
out_name_A = ort_session_A.get_outputs()
in_name_A0 = in_name_A[0].name
in_name_A1 = in_name_A[1].name
in_name_A2 = in_name_A[2].name
out_name_A0 = out_name_A[0].name
out_name_A1 = out_name_A[1].name
out_name_A2 = out_name_A[2].name
out_name_A3 = out_name_A[3].name
out_name_A4 = out_name_A[4].name
out_name_A5 = out_name_A[5].name
out_name_A6 = out_name_A[6].name


ort_session_B = onnxruntime.InferenceSession(onnx_model_B, sess_options=session_opts, providers=['DmlExecutionProvider'])

in_name_B = ort_session_B.get_inputs()
out_name_B = ort_session_B.get_outputs()
in_name_B0 = in_name_B[0].name
in_name_B1 = in_name_B[1].name
in_name_B2 = in_name_B[2].name
in_name_B3 = in_name_B[3].name
in_name_B4 = in_name_B[4].name
in_name_B5 = in_name_B[5].name
in_name_B6 = in_name_B[6].name
out_name_B0 = out_name_B[0].name


ort_session_C = onnxruntime.InferenceSession(onnx_model_C, sess_options=session_opts, providers=['CPUExecutionProvider'])
in_name_C = ort_session_C.get_inputs()
out_name_C = ort_session_C.get_outputs()
in_name_C0 = in_name_C[0].name
in_name_C1 = in_name_C[1].name
out_name_C0 = out_name_C[0].name


# Run F5-TTS by ONNX Runtime
audio, sr = torchaudio.load(reference_audio)
if sr != SAMPLE_RATE:
    resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=SAMPLE_RATE)
    audio = resampler(audio)
audio = audio.unsqueeze(0).numpy()
if "float16" in model_type:
   audio = audio.astype(np.float16)
zh_pause_punc = r"。，、；：？！"
ref_text_len = len(ref_text.encode('utf-8')) + 3 * len(re.findall(zh_pause_punc, ref_text))
gen_text_len = len(gen_text.encode('utf-8')) + 3 * len(re.findall(zh_pause_punc, gen_text))
ref_audio_len = audio.shape[-1] // HOP_LENGTH + 1
max_duration = np.array(ref_audio_len + int(ref_audio_len / ref_text_len * gen_text_len / SPEED), dtype=np.int64)
gen_text = convert_char_to_pinyin([ref_text + gen_text])
text_ids = list_str_to_idx(gen_text, vocab_char_map).numpy()
time_step = np.array(0, dtype=np.int32)

print("\n\nRun F5-TTS by ONNX Runtime.")
start_count = time.time()
noise, rope_cos, rope_sin, cat_mel_text, cat_mel_text_drop, qk_rotated_empty, ref_signal_len = ort_session_A.run(
        [out_name_A0, out_name_A1, out_name_A2, out_name_A3, out_name_A4, out_name_A5, out_name_A6],
        {
            in_name_A0: audio,
            in_name_A1: text_ids,
            in_name_A2: max_duration
        })
while time_step < NFE_STEP:
    print(f"NFE_STEP: {time_step}")
    noise = ort_session_B.run(
        [out_name_B0],
        {
            in_name_B0: noise,
            in_name_B1: rope_cos,
            in_name_B2: rope_sin,
            in_name_B3: cat_mel_text,
            in_name_B4: cat_mel_text_drop,
            in_name_B5: qk_rotated_empty,
            in_name_B6: time_step
        })[0]
    time_step += 1
generated_signal = ort_session_C.run(
        [out_name_C0],
        {
            in_name_C0: noise,
            in_name_C1: ref_signal_len
        })[0]
end_count = time.time()

# Save to audio
audio_tensor = torch.tensor(generated_signal, dtype=torch.float32).squeeze(0)
torchaudio.save(generated_audio, audio_tensor, SAMPLE_RATE)

print(f"\nAudio generation is complete.\n\nONNXRuntime Time Cost in Seconds:\n{end_count - start_count:.3f}")
