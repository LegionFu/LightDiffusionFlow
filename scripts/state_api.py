from fastapi import FastAPI, Body, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
import gradio as gr

import os, io, sys
import json
from PIL import Image
import re,base64,copy
import time,requests
import shutil
from urllib.parse import urlparse
import tempfile

from modules import localization, images
import modules.shared as shared
import modules.scripts as scripts
import modules.script_callbacks as script_callbacks
import modules.generation_parameters_copypaste as parameters_copypaste
from modules.generation_parameters_copypaste import paste_fields, registered_param_bindings, parse_generation_parameters
from modules.sd_models import checkpoints_list


from scripts import lightdiffusionflow_version, lightdiffusionflow_config
import scripts.lightdiffusionflow_config as lf_config

# current_path = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(os.path.join(current_path,"lib"))

workflow_json = {}
State_Comps = {} # 当前页面的按钮组件
invisible_buttons = {}
Webui_Comps = {} # webui上需要操作的图片组件
Webui_Comps_Cur_Val = [] # 顺序与Image_Components_Key一致
Output_Log = ""

conponents_originlist = []
extensions_conponents = {}
txt2img_script_container = None

Need_Preload = False
Preload_File = r""
File_extension = ".flow"

def test_func():
  print("test_func")
  # print(parameters_copypaste.paste_fields)

def add_output_log(msg:str="", style:str=""):
  global Output_Log
  if(msg != ""):
    #print(f"Output_Log: {msg}")
    Output_Log += f'<p style="{style}">{msg}</p>'

  return Output_Log, Output_Log

def find_checkpoint_from_name(name:str):

  for checkpoint in checkpoints_list.keys():
    res = re.search(r"(.+)\.(.+)", checkpoint)
    #print(checkpoint)
    #print(res.group(1))
    try:
      if(res.group(1) == name):
        return checkpoint
    except:
      pass
  return name

def find_checkpoint_from_hash(hash:str):

  for checkpoint in checkpoints_list.keys():
    res = re.search(r"\[([0-9a-fA-F]{10})\]", checkpoint)
    try:
      if(res.group(1) == hash):
        return checkpoint
    except:
      pass
  return hash

def set_lightdiffusionflow_file():
  global Preload_File
  return Preload_File


'''
python触发导入事件，按正常触发逻辑先执行js代码，把除图片以外的参数全部设置好，
然后回到python代码，读取图片保存到Webui_Comps_Cur_Val，
再用json2js的onchange事件触发js来点击隐藏按钮开始触发设置图片的事件队列。
'''
def on_after_component(component, **kwargs):
  global txt2img_script_container

  conponents_originlist.append(component)

  try:
    if(Webui_Comps.get(kwargs["elem_id"], None) == None):
      Webui_Comps[kwargs["elem_id"]] = component
  except BaseException as e:
    pass

  # if(kwargs["elem_id"] == "txt2img_script_container"):
  #   print(component)
  if(txt2img_script_container == None):
    temp = component
    i = 10
    while temp and i>0:
      if(temp.elem_id == "txt2img_script_container"):
        txt2img_script_container = temp
        break
      else:
        temp = temp.parent
        i-=1

  if (isinstance(component, gr.Button) and kwargs["elem_id"] == "change_checkpoint"): # 加载到最后一个组件了

    for group in txt2img_script_container.children:
      try:
        print(group.children[0].label)
        extensions_conponents[group.children[0].label] = []
      except:
        pass

    for comp in conponents_originlist:
      temp_parent  = comp.parent
      while temp_parent:
        try:
          if(extensions_conponents.get(temp_parent.label, None) != None):
            extensions_conponents[temp_parent.label].append(comp)
            break
        except:
          pass
        temp_parent = temp_parent.parent
    
    print(extensions_conponents) # 整理好的第三方插件用到的组件


    #print("LightDiffusionFlow绑定按钮")

    target_comps = []

    target_comps.append(State_Comps["json2js"]) # 触发事件传递json给js
    #target_comps.append(State_Comps["outlog"][0])
    #target_comps.append(State_Comps["outlog"][1]) # 因为显示日志的窗口分txt2img和img2img两个位置 所以两个位置同步导出

    for btn in State_Comps["export"]:
      btn.click(None,_js="state.core.actions.exportState") #, inputs=[],outputs=[] 

    for btn in State_Comps["import"]:
      # js里加载除图片以外的参数 python加载图片
      btn.upload(fn_import_workflow, _js=f"state.core.actions.handleLightDiffusionFlow",
        inputs=[btn],outputs=target_comps)

    State_Comps["json2js"].change(fn=None,_js="state.core.actions.startImportImage",
      inputs=[State_Comps["json2js"]])
    
    #State_Comps["test_button"].click(test_func,_js="state.utils.testFunction",inputs=[])

    State_Comps["refresh_log"].click(add_output_log,inputs=[],outputs=[State_Comps["outlog"][0], State_Comps["outlog"][1]])

    input_component = State_Comps["background_import"] #State_Comps["import"][0]
    State_Comps["set_file_button"].click(set_lightdiffusionflow_file,inputs=[],outputs=[input_component])
    State_Comps["preload_button"].click(fn_import_workflow, _js=f"state.core.actions.handleLightDiffusionFlow", 
      inputs=[input_component],outputs=target_comps)

    for key in invisible_buttons.keys():
      segs = key.split("_")
      comp_name = "_".join(segs[2:])
      #print(comp_name)
      try:
        invisible_buttons[key].click(func_for_invisiblebutton,
          inputs=[], 
          outputs=[
            Webui_Comps[comp_name], 
            State_Comps["json2js"], 
            State_Comps["outlog"][0], 
            State_Comps["outlog"][1]
          ])
      except KeyError:
        print(f"No such component: {comp_name}")


temp_index = -1
next_index = -1
def func_for_invisiblebutton():
  global temp_index,next_index
  global Webui_Comps_Cur_Val, Output_Log

  temp_index = next_index+1
  next_index = temp_index

  try:
    while( next_index < len(Webui_Comps_Cur_Val) and Webui_Comps_Cur_Val[next_index+1] == None ):
      next_index += 1
  except:
    pass
  
  # try:
  #   print(f"func_for_invisiblebutton {temp_index} {next_index} {len(Webui_Comps_Cur_Val)}")
  #   print(f"func_for_invisiblebutton {lf_config.Image_Components_Key[temp_index]} {Webui_Comps_Cur_Val[temp_index]} ")
  # except:
  #   pass
  
  
  # 第一个组件是用来预计算第一张图的索引 防止出现有没用的页面跳转 所以不用输出日志信息
  if(temp_index > 0):
    add_output_log(f"importing image: \'{lf_config.Image_Components_Key[temp_index]}\' ") 
    
  if(next_index+1 == len(Webui_Comps_Cur_Val)):
    add_output_log(f"import completed!")
  
  # 因为显示日志的窗口分txt2img和img2img两个位置 所以两个位置同步导出
  return Webui_Comps_Cur_Val[temp_index], next_index, Output_Log, Output_Log 


def fn_import_workflow(workflow_file):
  global workflow_json, Output_Log
  global Webui_Comps_Cur_Val, temp_index, next_index
  temp_index = -1 # 重置索引
  next_index = -1
  
  workflow_json = {}
  if(workflow_file):
    try:
      config_file = workflow_file[0].name
    except:
      config_file = workflow_file.name

    print("fn_import_workflow "+str(config_file))
    if (os.path.splitext(config_file)[-1] in  [File_extension, ".lightflow", ".json"]): # 兼容部分旧版本文件
      with open(config_file, mode='r', encoding='UTF-8') as f:
        json_str = f.read()
        workflow_json = json.loads(json_str)
    else:
      print("invalid file!")

  Webui_Comps_Cur_Val = []
  for key in lf_config.Image_Components_Key:
    image = None
    successed = 2
    tempkey = key
    while successed > 0:
      try:
        image_data = workflow_json[key]
        matchObj = re.match("data:image/[a-zA-Z0-9]+;base64,",image_data)
        if matchObj != None:
          image_data = image_data[len(matchObj.group()):]
        image_data = base64.decodebytes(image_data.encode('utf-8'))
        image = Image.open(io.BytesIO(image_data))
        successed = 0
      except:
        # 如果是controlnet 第一张图 就修改一下key值重试一遍
        if(key == "txt2img_controlnet_ControlNet_input_image"):
          key = "txt2img_controlnet_ControlNet-0_input_image"
        elif(key == "img2img_controlnet_ControlNet_input_image"):
          key = "img2img_controlnet_ControlNet-0_input_image"

        elif(key == "txt2img_controlnet_ControlNet-0_input_image"):
          key = "txt2img_controlnet_ControlNet_input_image"
        elif(key == "img2img_controlnet_ControlNet-0_input_image"):
          key = "img2img_controlnet_ControlNet_input_image"
        else:
          successed = 0
      successed-=1
    
    Webui_Comps_Cur_Val.append(image)

  # return_vals.append(str(time.time())) # 用来触发json2js事件，python设置完图片 js继续设置其他参数  弃用
  # return tuple(return_vals)
  return str(temp_index)#, Output_Log, Output_Log

class imgs_callback_params(BaseModel):
  id:str
  img:str

class png_info_params(BaseModel):
  img_path:str

class file_params(BaseModel):
  file_path:str

class StateApi():

  BASE_PATH = '/lightdiffusionflow'

  def get_path(self, path):
    return f"{self.BASE_PATH}{path}"

  def add_api_route(self, path: str, endpoint, **kwargs):
    return self.app.add_api_route(self.get_path(path), endpoint, **kwargs)

  def start(self, _: gr.Blocks, app: FastAPI):
    print("-----------------state_api start------------------")

    self.app = app 
    # 读取本地的config.json
    self.add_api_route('/local/config.json', self.get_config, methods=['GET']) 
    # python已经加载好的配置workflow_json  发送给 js
    self.add_api_route('/local/lightdiffusionflow_config', self.get_lightdiffusionflow_config, methods=['GET']) 
    # 获取图片的组件id 由js来设置onchange事件
    self.add_api_route('/local/get_imgs_elem_key', self.get_img_elem_key, methods=['GET']) 
    # 用户设置了新图片 触发回调保存到 workflow_json
    self.add_api_route('/local/imgs_callback', self.imgs_callback, methods=['POST']) 
    # 刷新页面之后触发
    self.add_api_route('/local/refresh_ui', self.refresh_ui, methods=['GET']) 
    self.add_api_route('/local/output_log', add_output_log, methods=['GET']) 
    self.add_api_route('/local/png_info', self.png_info, methods=['POST']) # 
    # 传入一个文件路径，返回文件内容
    self.add_api_route('/local/read_file', self.read_file, methods=['POST']) 
    self.add_api_route('/local/need_preload', self.need_preload, methods=['GET'])

    self.add_api_route('/set_preload', self.set_preload, methods=['POST'])

  def get_config(self):
    return FileResponse(shared.cmd_opts.ui_settings_file)

  def get_lightdiffusionflow_config(self, onlyimg:bool = False):
    global workflow_json
    temp_json = {}
    if(onlyimg):
      for key in lf_config.Image_Components_Key:
        try:
          temp_json[key] = workflow_json[key]
        except:
          pass
    else:
      temp_json = copy.deepcopy(workflow_json)
      for key in lf_config.Image_Components_Key:
        temp_json[key] = ""

    return json.dumps(temp_json)

  def str_2_json(self, str_data:str):
    out_json = {}
    res = re.findall(r"([^:]+:[^:]{1,})(,|$)",str_data)
    for field in res:
      data = field[0].split(":")
      try:
        out_json[data[0].strip()] = data[1].strip()
      except IndexError as e:
        print(f"str_2_json [key error]: {e}")
    return out_json

  def png_info(self, img_data:png_info_params):

    geninfo, items = images.read_info_from_image(Image.open(img_data.img_path))
    geninfo = parse_generation_parameters(geninfo)
    temp_json = {}
    for key in geninfo.keys():
      
      matchObj = re.match("ControlNet ([0-9])", key)
      if(matchObj != None): # controlnet
        cn_info = self.str_2_json(geninfo[key])
        if(len(cn_info.keys()) > 0):
          temp_json["state-ext-control-net-txt2img_0-enable".replace("0",matchObj.group(1))] = True

        for cn_key in cn_info.keys():
          if(cn_key == "starting/ending"):
            cn_key_split = cn_key.split("/")
            data = cn_info[cn_key].replace("(","").replace(")","").split(",")
            temp_json[lf_config.PNGINFO_CN_2_LIGHTDIFFUSIONFLOW[cn_key_split[0]].replace("0",matchObj.group(1))]\
               = data[0].strip()
            temp_json[lf_config.PNGINFO_CN_2_LIGHTDIFFUSIONFLOW[cn_key_split[1]].replace("0",matchObj.group(1))]\
               = data[1].strip()
          elif(cn_key == "pixel perfect"):
            temp_json[lf_config.PNGINFO_CN_2_LIGHTDIFFUSIONFLOW[cn_key].replace("0",matchObj.group(1))]\
               = (cn_info[cn_key].lower() == "true")
          else:
            try:
              temp_json[lf_config.PNGINFO_CN_2_LIGHTDIFFUSIONFLOW[cn_key.lower()].replace("0",matchObj.group(1))] = cn_info[cn_key]
            except KeyError as e:
              print(f"ControlNet option '{cn_key}' parsing failed.")

      elif(key == "Model hash"):
        target_model = find_checkpoint_from_hash(geninfo[key])
        if(target_model == geninfo[key]):#说明没有找到相同hash值的模型，改用名称查找
          try:
            target_model = find_checkpoint_from_name(geninfo["Model"])
          except:
            pass
        temp_json[lf_config.PNGINFO_2_LIGHTDIFFUSIONFLOW[key]] = target_model

      elif(key == "Face restoration"):
        temp_json[lf_config.PNGINFO_2_LIGHTDIFFUSIONFLOW[key]] = True
      else:
        try:
          temp_json[lf_config.PNGINFO_2_LIGHTDIFFUSIONFLOW[key]] = geninfo[key]
        except KeyError as e:
          pass
          #print(e)
      
      if(key in ["Hires upscale","Hires steps","Hires upscaler","Hires resize-1","Hires resize-2"]):
        temp_json["state-txt2img_enable_hr"] = True

    return json.dumps(temp_json)

  def read_file(self, params:file_params):

    file_content = ""
    with open(params.file_path, mode='r', encoding='UTF-8') as f:
      file_content = f.read()
      
    return file_content

  def get_img_elem_key(self):
    keys_str = ",".join(lf_config.Image_Components_Key)
    return keys_str

  def imgs_callback(self, img_data:imgs_callback_params):
    global workflow_json
    workflow_json[img_data.id] = img_data.img

  def refresh_ui(self):
    global workflow_json, Output_Log
    workflow_json = {}
    Output_Log = ""
    print("refresh_ui")

  def set_preload(self, params:file_params):
    global Need_Preload,Preload_File
    print(params.file_path)
    res = "OK"
    if(params.file_path):
      if(os.path.exists(params.file_path)):
        Preload_File = params.file_path
        Need_Preload = True
        res = "OK,Local File!"
      else:
        response = requests.get(params.file_path)
        if(response.status_code == 200):
          parsed_url = urlparse(params.file_path)
          file_name = os.path.basename(parsed_url.path)
          tempdir = os.path.join(tempfile.gettempdir(),"lightdiffusionflow_temp")
          if(os.path.exists(tempdir)):
            shutil.rmtree(tempdir)
          if(not os.path.exists(tempdir)):
            os.mkdir(tempdir)
          temp_file = os.path.join(tempdir,file_name)
          
          with open(temp_file,"wb") as f:
            f.write(response.content)
          
          print(temp_file)
          Preload_File = temp_file
          Need_Preload = True
          res = "OK,Network File!"
        else:
          res = "Invalid File!"

    return res

  def need_preload(self):
    global Need_Preload,Preload_File
    if(Need_Preload):
      Need_Preload = False
      return Preload_File
    return ""


class Script(scripts.Script):  

  def __init__(self) -> None:
    super().__init__()

  def title(self):
    return "lightdiffusionflow plugin"

  def show(self, is_img2img):
    return scripts.AlwaysVisible

  def ui(self, is_img2img):
    global File_extension
    print("----------------------ui---------------------------")
    try:
      State_Comps["import"]
      State_Comps["export"]
      State_Comps["outlog"]
    except:
      State_Comps["import"] = []
      State_Comps["export"] = []
      State_Comps["outlog"] = []

    with gr.Accordion('LightDiffusionFlow '+lightdiffusionflow_version.lightdiffusionflow_version, open=True, visible=True):
      with gr.Row():
        lightdiffusionflow_file = gr.File(label="LightDiffusionFlow File",file_count="single", file_types=[File_extension])
        State_Comps["import"].append(lightdiffusionflow_file)
        
        with gr.Column(scale=1):
          gr.HTML(label="",value='''
          <a style ="text-decoration:underline;color:cornflowerblue;",
          href="https://www.lightflow.ai/">开源社区</a>''')
          State_Comps["outlog"].append(gr.HTML(label="Output Log",value='''
          <p style=color:Tomato;>Welcome to LightDiffusionFlow!  \(^o^)/~</p>
          <p style=color:MediumSeaGreen;>Welcome to LightDiffusionFlow!  \(^o^)/~</p>
          <p style=color:DodgerBlue;>Welcome to LightDiffusionFlow!  \(^o^)/~</p>'''))

      with gr.Row():
        export_config = gr.Button(value='Export')
        State_Comps["export"].append(export_config)

      if(not is_img2img):
        
        State_Comps["background_import"] = gr.File(label="LightDiffusionFlow File",file_count="single",
           file_types=[File_extension],visible=False)

        State_Comps["json2js"] = gr.Textbox(label="json2js",visible=False)

        #State_Comps["test_button"] = gr.Button(value='测试',elem_id='test_button',visible=False)

        State_Comps["refresh_log"] = gr.Button(value='刷新日志',elem_id='txt2img_invisible_refresh_log',visible=False)

        State_Comps["set_file_button"] = gr.Button(value='设置文件',elem_id='set_lightdiffusionflow_file',visible=False)
        State_Comps["preload_button"] = gr.Button(value='预加载',elem_id='preload_button',visible=False)

        with gr.Row():
          State_Comps["useless_Textbox"] = \
            gr.Textbox(value='useless_Textbox', elem_id='useless_Textbox', visible=False)
          
          for key in lf_config.Image_Components_Key:
            elem_id = ("img2img_" if is_img2img else "txt2img_") + "invisible_" + key
            invisible_buttons[elem_id] = gr.Button(value=elem_id, elem_id=elem_id, visible=False)


def on_before_reload():
  lightdiffusionflow_config.init()

# add callbacks
api = StateApi()
script_callbacks.on_app_started(api.start)
script_callbacks.on_after_component(on_after_component)
script_callbacks.on_before_reload(on_before_reload)