import asyncio

from asyncio.windows_events import NULL
from cmd import PROMPT
import urllib.request
import json
from krita import *
from PyQt5.Qt import QByteArray
from PyQt5.QtGui  import QImage, QPixmap
import array
from copy import copy, deepcopy

import asyncio.events as events
import os
import sys
import threading
from contextlib import contextmanager, suppress
from heapq import heappop
from os.path import exists

# Stable Diffusion Plugin fpr Krita
# (C) 2022, Nicolay Mausz
# MIT License
#
rPath= Krita.instance().readSetting("","ResourceDirectory","")

class ModifierData:    
    list=[]
    tags=[]
    def serialize(self):
        obj={"list":self.list,"tags":self.tags}
        return json.dumps(obj)
    def unserialize(self,str):
        obj=json.loads(str)
        self.list=obj["list"]
        self.tags=obj["tags"]
    def save(self):
        str=self.serialize(self)
        with open(rPath+"/krita_ai_modifiers.config", 'w', encoding='utf-8') as f_out:
            f_out.write(str)
    def load(self):
        if (not exists(rPath+"/krita_ai_modifiers.config")): return
        with open(rPath+"/krita_ai_modifiers.config", 'r', encoding='utf-8') as f_in:
            str=f_in.read()
        self.unserialize(self,str)    

class SDConfig:
    "This is Stable Diffusion Plugin Main Configuration"     
    url = "http://localhost:7860"
    type="Colab"
    inpaint_mask_blur=4
    inpaint_mask_content="latent noise"     
    width=512
    height=512    
    dlgData={
        "mode": "txt2img",
        "prompt": "",
        "seed": "",
        "steps": 15,
        "steps_update": 50,
        "num": 2,
        "modifiers": "highly detailed\n",
        "cfg_value": 7.5,
        "strength": .75,
        "sampling_method":"LMS"
    }


    def serialize(self):
        obj={"url":self.url,"type":self.type,
        "inpaint_mask_blur":self.inpaint_mask_blur, "inpaint_mask_content":self.inpaint_mask_content,
        "width":self.width, "height":self.height,
        "type": self.type,
        "dlgData":self.dlgData}
        return json.dumps(obj)
    def unserialize(self,str):
        obj=json.loads(str)
        self.url=obj.get("url","http://localhost:7860")
        self.type=obj.get("type","Colab")
        self.dlgData=obj["dlgData"]
        self.inpaint_mask_blur=obj.get("inpaint_mask_blur",4)
        self.inpaint_mask_content=obj.get("inpaint_mask_content","latent noise")
        self.width=obj.get("width",512)
        self.height=obj.get("height",512)
    def save(self):
        str=self.serialize(self)
        with open(rPath+"/krita_ai.config", 'w', encoding='utf-8') as f_out:
            f_out.write(str)
    def load(self):
        if (not exists(rPath+"/krita_ai.config")): return
        with open(rPath+"/krita_ai.config", 'r', encoding='utf-8') as f_in:
            str=f_in.read()
        self.unserialize(self,str)

SDConfig.load(SDConfig)

class SDParameters:
    "This is Stable Diffusion Parameter Class"     
    prompt = ""
    steps = 0
    seed = 0
    num =0
    sampling_method="LMS",
    seedList =["","","",""]
    imageDialog = NULL
    regenerate = False
    image64=""
    maskImage64=""
    sampling_method="LMS"
    inpaint_mask_blur=4
    inpaint_mask_content="latent noise" 
    mode="txt2img"    

def errorMessage(text,detailed):
    msgBox= QMessageBox()
    msgBox.resize(500,200)
    msgBox.setWindowTitle("Stable Diffusion")
    msgBox.setText(text)
    msgBox.setDetailedText(detailed)
    msgBox.setStyleSheet("QLabel{min-width: 700px;}")
    msgBox.exec()


class SDConfigDialog(QDialog):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("Stable Diffusion Configuration")
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        link_label=QLabel('Webservice URL<br>\nYou need running <a href="https://colab.research.google.com/drive/1BKkFN5OOXydrFAxYJcbPdGrVuQVdJpt_#scrollTo=bYpxm4Fw2tLT">Colab</a><br>\nCheck if web interface is working there before you use this plugin. Use https://xxx.gradio.app link here.')
        link_label.setOpenExternalLinks(True)
        self.layout.addWidget(link_label)
        self.url = QLineEdit()
        self.url.setText(SDConfig.url)    
        self.layout.addWidget(self.url)
        self.layout.addWidget(QLabel('Type'))
        self.type = QComboBox()
        self.type.addItems(['Colab', 'Local'])
        self.type.setCurrentText(SDConfig.type)
        self.layout.addWidget(self.type,stretch=1)      
        self.layout.addWidget(QLabel('For local experimental version you need this fork running <br> <a href="https://github.com/imperator-maximus/stable-diffusion-webui">imperator-maximus/stable-diffusion-webui</a><br>\nIf it gets connection error - this is known issue and I am working on it. If it works fine - let me know :)'))

        self.layout.addWidget(QLabel(''))
        

        inpainting_label=QLabel('Inpainting options')
        inpainting_label.setToolTip('You can play around with these two values. Default is 4 and "latent noise"')
        self.layout.addWidget(inpainting_label)
        h_layout_inpaint=QHBoxLayout()

        self.inpaint_mask_blur=QLineEdit()
        self.inpaint_mask_blur.setText(str(SDConfig.inpaint_mask_blur))
        h_layout_inpaint.addWidget(QLabel('Mask Blur:'),stretch=1)
        h_layout_inpaint.addWidget(self.inpaint_mask_blur,stretch=1)
        h_layout_inpaint.addWidget(QLabel('Masked Content:'),stretch=1)
        self.inpaint_mask_content = QComboBox()
        self.inpaint_mask_content.addItems(['fill', 'original', 'latent noise', 'latent nothing'])
        self.inpaint_mask_content.setCurrentText(SDConfig.inpaint_mask_content)
        h_layout_inpaint.addWidget(self.inpaint_mask_content,stretch=1)      
        h_layout_inpaint.addWidget(QLabel(''),stretch=5)

        self.layout.addLayout(h_layout_inpaint)

        self.layout.addWidget(QLabel(''))
        self.layout.addWidget(QLabel('Please do not change these. Only if you really know what you do - otherwise let it to default 512x512'))
        h_layout_size=QHBoxLayout()
        h_layout_size.addWidget(QLabel('Width:'))
        self.width=QLineEdit()
        self.width.setText(str(SDConfig.width))       
        h_layout_size.addWidget(self.width)
        h_layout_size.addWidget(QLabel('Height:'))
        self.height=QLineEdit()
        self.height.setText(str(SDConfig.height))
        h_layout_size.addWidget(self.height)
        h_layout_size.addWidget(QLabel(''),stretch=5)

        self.layout.addLayout(h_layout_size)
        self.layout.addWidget(QLabel(''))
        self.layout.addWidget(QLabel(''))

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        self.resize(500,200)
    def save(self):
        SDConfig.url=self.url.text()
        SDConfig.inpaint_mask_blur=int(self.inpaint_mask_blur.text())
        SDConfig.inpaint_mask_content=self.inpaint_mask_content.currentText()
        SDConfig.width=int(self.width.text())
        SDConfig.height=int(self.height.text())
        SDConfig.type=self.type.currentText()

        SDConfig.save(SDConfig)

class ModifierDialog(QDialog):
    def __init__(self):
        super().__init__(None)
        self.setWindowTitle("Stable Diffusion Modifier list")
        self.resize(800,500)
        QBtn =  QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.rejected.connect(self.reject)
        grid_layout = QVBoxLayout()
        self.layout=QVBoxLayout()
        self.setLayout(self.layout)

        ModifierData.load(ModifierData)
        self.layout.addLayout(grid_layout)
        for i in range(0,len(ModifierData.list)):
            entry=ModifierData.list[i]
            mod_layout=QVBoxLayout()
            mod_layout.addWidget(QLabel(entry["name"]))
            btn_h_layout=QHBoxLayout()
            btnSelect = QPushButton("")
            btnSelect.setIcon( Krita.instance().icon('select'))        
            btn_h_layout.addWidget(btnSelect,stretch=1)
            btnDelete = QPushButton("")
            btnDelete.setIcon( Krita.instance().icon('deletelayer'))   
            btnSelect.clicked.connect(lambda ch, num=i: self.selectModifier(num))
            btnDelete.clicked.connect(lambda ch, num=i: self.deleteModifier(num))

            btn_h_layout.addWidget(btnDelete,stretch=1)
            btn_h_layout.addWidget(QLabel(""),stretch=5)

            mod_layout.addLayout(btn_h_layout)
            grid_layout.addLayout(mod_layout)

        self.layout.addWidget(QLabel("Name"))
        self.name = QLineEdit()
#        self.name.setText(selected_mod["name"])       
        self.layout.addWidget(self.name) 
   
        self.layout.addWidget(QLabel("Modifiers"))
        self.modifiers=QPlainTextEdit()
        self.modifiers.setPlainText(SDConfig.dlgData.get("modifiers",""))      
        self.layout.addWidget(self.modifiers)     

        self.layout.addWidget(QLabel("Example Prompt"))
        self.example_prompt = QLineEdit()
        self.example_prompt.setText(SDConfig.dlgData.get("prompt",""))       
        self.layout.addWidget(self.example_prompt) 
        h_layout = QHBoxLayout()
        button_save=QPushButton("Add and Select") 
        h_layout.addWidget(button_save)
        self.layout.addLayout(h_layout)
        button_save.clicked.connect(lambda ch, : ModifierDialog.addModifier(self))
        self.layout.addWidget(QLabel(""))        
        self.layout.addWidget(self.buttonBox)
    def addModifier(self):        
        if (not self.name): return
        mod_info={"name":self.name.text(),"modifiers":self.modifiers.toPlainText()}
        ModifierData.list.append(mod_info)
        ModifierData.save(ModifierData)
        SDConfig.dlgData["modifiers"]=self.modifiers.toPlainText()
        self.accept()
    def selectModifier(self,num):
        mod_info=ModifierData.list[num]
        SDConfig.dlgData["modifiers"]=mod_info["modifiers"]
        self.accept()
    def deleteModifier(self,num):
        qm = QMessageBox()
        ret = qm.question(self,'', "Are you sure?", qm.Yes | qm.No)
        if ret == qm.Yes:
            del ModifierData.list[num]
            ModifierData.save(ModifierData)
            self.accept()

    def modifierInput(self,layout):
        layout.addWidget(QLabel("Modifiers"))
        modifiers=QPlainTextEdit()
        modifiers.setPlainText(SDConfig.dlgData.get("modifiers",""))      
        layout.addWidget(modifiers)
        h_layout = QHBoxLayout()
        button_presets=QPushButton("Presets...") 
        h_layout.addWidget(button_presets)
        button_copy_prompt=QPushButton("Copy full Prompt") 
        h_layout.addWidget(button_copy_prompt)        
        layout.addLayout(h_layout)
        button_presets.clicked.connect(lambda ch, : ModifierDialog.openModifierPresets(self))
        button_copy_prompt.clicked.connect(lambda ch, : ModifierDialog.copyPrompt(self))
        return modifiers        

    def copyPrompt(self):
        prompt=getFullPrompt(self)
        QApplication.clipboard().setText(prompt)

    def openModifierPresets(self):
        SDConfig.dlgData["modifiers"]=self.modifiers.toPlainText()
        dlg=ModifierDialog()
        if dlg.exec():            
            self.modifiers.setPlainText(SDConfig.dlgData["modifiers"])


# default dialog for image generation: txt2img, img2img and inpainting
class SDDialog(QDialog):
    def __init__(self,mode,image):
        super().__init__(None)
        SDConfig.dlgData["mode"]=mode
        data=SDConfig.dlgData

        self.setWindowTitle("Stable Diffusion "+data["mode"])

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QHBoxLayout()
        formLayout= QVBoxLayout()
        self.layout.addLayout(formLayout)
        formLayout.addWidget(QLabel("Prompt"))
        self.prompt = QLineEdit()
        self.prompt.setText(data["prompt"])            
        formLayout.addWidget(self.prompt)
        self.modifiers= ModifierDialog.modifierInput(self,formLayout)
        if (data["mode"]=="img2img"):
            formLayout.addWidget(QLabel("Denoising Strength"))        
            self.strength=self.addSlider(formLayout,data["strength"]*100,0,100,1,100)

        steps_label=QLabel("Steps")
        steps_label.setToolTip("more steps = slower but often better quality. Recommendation start with lower step like 15 and update in image overview with higher one like 50")

        formLayout.addWidget(steps_label)        
        self.steps=self.addSlider(formLayout,data["steps"],1,250,5,1)
        formLayout.addWidget(QLabel("Number images"))        
        self.num=self.addSlider(formLayout,data["num"],1,4,1,1)


        formLayout.addWidget(QLabel(""))        

        formLayout.addWidget(QLabel("Advanced"))        
        seed_label=QLabel("Seed (empty=random)")
        seed_label.setToolTip("same seed and same prompt = same image")
        formLayout.addWidget(seed_label)      
        self.seed = QLineEdit()
        self.seed.setText(data["seed"])                  
        formLayout.addWidget(self.seed)   
        cfg_label=QLabel("Guidance Scale")
        cfg_label.setToolTip("how strongly the image should follow the prompt")
        formLayout.addWidget(cfg_label)        
        self.cfg_value=self.addSlider(formLayout,data["cfg_value"]*10,10,300,5,10)

   
        cfg_label=QLabel("Sampling method")
        cfg_label.setToolTip("")
        formLayout.addWidget(cfg_label)           
        self.sampling_method = QComboBox()
        self.sampling_method.addItems(['LMS', 'Euler a', 'Euler', 'Heun','DPM2','DPM2 a','DDIM','PLMS'])
        self.sampling_method.setCurrentText(data.get("sampling_method","LMS"))
        formLayout.addWidget(self.sampling_method)           
        formLayout.addWidget(QLabel(""))        
        formLayout.addWidget(self.buttonBox)
        if (not data["mode"]=="txt2img"):
            imgLabel=QLabel()        
            self.layout.addWidget(imgLabel) 
            imgLabel.setPixmap(QPixmap.fromImage(image))  
        self.setLayout(self.layout)

    def addSlider(self,layout,value,min,max,steps,divider):
        h_layout =  QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal, self)
        slider.setRange(min, max)

        slider.setSingleStep(steps)
        slider.setPageStep(steps)
        slider.setTickInterval
        label = QLabel(str(value), self)
        h_layout.addWidget(slider, stretch=9)
        h_layout.addWidget(label, stretch=1)
        if (divider!=1):
            slider.valueChanged.connect(lambda: slider.setValue(slider.value()//steps*steps) or label.setText( str(slider.value()/divider)))
        else:
            slider.valueChanged.connect(lambda: slider.setValue(slider.value()//steps*steps) or label.setText( str(slider.value())))
        slider.setValue(int(value))
        layout.addLayout(h_layout)
        return slider
    # put data from dialog in configuration and save it        
    def setDlgData(self):
        SDConfig.dlgData["prompt"]=self.prompt.text()
        SDConfig.dlgData["steps"]=int(self.steps.value())
        SDConfig.dlgData["seed"]=self.seed.text()
        SDConfig.dlgData["num"]=int(self.num.value())
        SDConfig.dlgData["cfg_value"]=self.cfg_value.value()/10
        SDConfig.dlgData["modifiers"]=self.modifiers.toPlainText()
        SDConfig.dlgData["sampling_method"]=self.sampling_method.currentText()
        
        if SDConfig.dlgData["mode"]=="img2img": 
            SDConfig.dlgData["strength"]=self.strength.value()/100
        SDConfig.save(SDConfig)
# put image in Krita on new layer or existing one
def selectImage(p: SDParameters,qImg):  
    d = Application.activeDocument()
    n = d.activeNode()
    s = d.selection()        
    print("result at :",s.x(),s.y(),"width,height:",s.width(),s.height())
    root = d.rootNode()
    n = d.createNode(p.prompt, "paintLayer")
    root.addChildNode(n, None)

    if (p.mode=="img2img" or p.mode=="inpainting"):
        qImg = qImg.scaled(s.width(), s.height())
    else:
        qImg = qImg.scaled(s.width(), s.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    ptr = qImg.bits()
    ptr.setsize(qImg.byteCount())           
    n.setPixelData(QByteArray(ptr.asstring()),s.x(),s.y(),qImg.width(),qImg.height())
    d.waitForDone ()
    d.refreshProjection() 

# asking for image of result set and update option
class showImages(QDialog):
    def __init__(self,qImgs,p: SDParameters):
        super().__init__(None)
        self.qImgs=qImgs
        self.setWindowTitle("Result")
        QBtn =  QDialogButtonBox.Cancel
        self.SDParam=p
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        top_layout=QVBoxLayout()        
        prompt_layout=QHBoxLayout()        
        top_layout.addLayout(prompt_layout)
        self.prompt = QLineEdit()
        self.prompt.setText(SDConfig.dlgData.get("prompt",""))
        prompt_layout.addWidget(self.prompt,stretch=9)
        btn_regenerate=QPushButton("Generate with steps "+str(SDConfig.dlgData["steps"]))         
        btn_regenerate.clicked.connect(self.regenerateStart)
        prompt_layout.addWidget(btn_regenerate,stretch=1)
        self.modifiers= ModifierDialog.modifierInput(self,top_layout)

        layout=QHBoxLayout()
        top_layout.addLayout(layout)
        self.imgLabels=[0]*p.num
        self.seedLabel=[0]*p.num
        self.qImgs=qImgs
        i=0
        for qImg in qImgs:       
            v_layout = QVBoxLayout()
            layout.addLayout(v_layout)       
            imgLabel=QLabel()
            v_layout.addWidget(imgLabel) 
            imgLabel.setPixmap(QPixmap.fromImage(qImg).scaled(380,380,Qt.KeepAspectRatio))  
            seedLabel=QLabel(p.seedList[i])
            seedLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.seedLabel[i]=seedLabel
            v_layout.addWidget(seedLabel)     
            self.imgLabels[i]=imgLabel
            h_layout = QHBoxLayout()
            v_layout.addLayout(h_layout)               
            btn=QPushButton("Select")          
            h_layout.addWidget(btn,stretch=1)
            btn.clicked.connect(lambda ch, num=i: selectImage(p,self.qImgs[num]))
            btnUpdate=QPushButton()  
            btnUpdate.setIcon( Krita.instance().icon('updateColorize'))        
            h_layout.addWidget(btnUpdate,stretch=1)
            btnUpdate.clicked.connect(lambda ch, num=i: self.updateImageStart(num))
            i=i+1
            
        #layout.addWidget(self.buttonBox)
        top_layout.addWidget(QLabel("Update one image with new Steps value"))
        self.steps_update=SDDialog.addSlider(self,top_layout,SDConfig.dlgData.get("steps_update",50),1,250,5,1)
        
        if (p.mode=="img2img"):
            top_layout.addWidget(QLabel("Update with new Strengths value"))
            self.strength_update=SDDialog.addSlider(self,top_layout,SDConfig.dlgData.get("strength",0.5)*100,0,100,1,100)

        self.setLayout(top_layout)
    # start request for HQ version of one image
    def regenerateStart(self):
        p = copy(self.SDParam)
        #SDConfig.dlgData["steps_update"]=self.steps_update.value()
        #p.steps=SDConfig.dlgData["steps_update"]
        #SDConfig.save(SDConfig)
        SDConfig.dlgData["prompt"]=self.prompt.text()
        SDConfig.dlgData["modifiers"]=self.modifiers.toPlainText()
        SDConfig.save(SDConfig)
        p.prompt= getFullPrompt(self)        
        p.imageDialog=self
        p.regenerate=True
        asyncio.run(runSD(p))

    def updateImages(self,qImgs,seeds):
        i=0
        self.qImgs=qImgs
        self.SDParam.seedList=seeds
        for qImg in qImgs:
            imgLabel=self.imgLabels[i]
            seedLabel=self.seedLabel[i]
            seedLabel.setText(seeds[i])
            imgLabel.setPixmap(QPixmap.fromImage(qImg).scaled(380,380,Qt.KeepAspectRatio))  
            i=i+1
    # update one single image with new parameters
    def updateImageStart(self,num):
        p = copy(self.SDParam)
        p.seed=p.seedList[num]
        if (p.mode=="img2img"): 
            p.strength=self.strength_update.value()/100
        SDConfig.dlgData["steps_update"]=self.steps_update.value()
        SDConfig.save(SDConfig)
        p.num=1
        p.steps=SDConfig.dlgData["steps_update"]
        SDConfig.dlgData["prompt"]=self.prompt.text()
        SDConfig.dlgData["modifiers"]=self.modifiers.toPlainText()
        p.prompt= getFullPrompt(self)        
        self.updateImageNum=num
        p.imageDialog=self
        asyncio.run(runSD(p))

    # update image with HQ version       
    def updateImage(self,qImg):
        num=self.updateImageNum
        imgLabel=self.imgLabels[num]
        self.qImgs[num]=qImg
        imgLabel.setPixmap(QPixmap.fromImage(qImg).scaled(380,380,Qt.KeepAspectRatio))  


def imageResultDialog(qImgs,p):
    dlg = showImages(qImgs,p)
    if dlg.exec():
        print("HQ Update here")
    else:
        print("Cancel!")
    return 3     
 
 # convert image from server result into QImage
def base64ToQImage(data):
     data=data.split(",")[1] # get rid of data:image/png,
     image64 = data.encode('ascii')
     imagen = QtGui.QImage()
     bytearr = QtCore.QByteArray.fromBase64( image64 )
     imagen.loadFromData( bytearr, 'PNG' )      
     return imagen



async def runSD(p: SDParameters):
    # dramatic interface change needed!
    Colab=True
    if (SDConfig.type=="Local"): Colab=False
    endpoint=SDConfig.url
    endpoint+="/api/predict/" 
    endpoint=endpoint.replace("////","//")
    if (not p.seed): seed=-1
    else: seed=int(p.seed)

    if (p.mode=="img2img"):
        # localhost
        j={
            "fn_index":8,
            "data":[p.prompt,p.image64,{"image":p.image64,"mask":p.image64},p.steps,p.sampling_method,4,"latent noise",False,"Redraw whole image",
                    p.num,1,p.cfg_value,p.strength,seed,SDConfig.height,SDConfig.width,"Just resize","RealESRGAN",64,True,
                    "Inpaint masked","None",8,4,"fill",False,"Seed","","Steps",""
            ]
        }
        # colab
        if (Colab):
            j={
                "fn_index":8,
                "data":[p.prompt,p.image64,None,p.steps,p.sampling_method,4,"latent noise",False,"Redraw whole image",
                        p.num,1,p.cfg_value,p.strength,seed,SDConfig.height,SDConfig.width,"Just resize","RealESRGAN",64,False,
                        "Inpaint masked","None",False,8,4,"fill","Seed","","Steps",""
                ]
            }        


    if (p.mode=="inpainting"):
        # localhost
        j={
            "fn_index":8,
            "data":[p.prompt,None,{"image":p.image64,"mask":p.maskImage64},p.steps,"Euler a",4,"latent noise",False,"Inpaint a part of image",p.num,1,p.cfg_value,0.75,seed,512,512,
            "Just resize","RealESRGAN",64,False,"Inpaint masked","None",8,4,"fill",False,"Seed","","Steps",""]
        }            
        # colab
        if (Colab):
            j={
                "fn_index":8,
                "data":[p.prompt,None,{"image":p.image64,"mask":p.maskImage64},p.steps,"Euler a",4,"latent noise",False,"Inpaint a part of image",p.num,1,p.cfg_value,0.75,seed,512,512,
                "Just resize","RealESRGAN",64,False,"Inpaint masked","None",False,8,4,"fill","Seed","","Steps",""]
            }    
   

    if (p.mode=="txt2img"):
        j={
            "fn_index":2,
            "data":[p.prompt,"",p.steps,p.sampling_method,False,p.num,1,p.cfg_value,seed,SDConfig.height,SDConfig.width,"None",False,"Seed","","Steps",""]
        }           
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    #print(j)
    data = json.dumps(j).encode("utf-8")
    try:
        req = urllib.request.Request(endpoint, data, headers)
        with urllib.request.urlopen(req) as f:
            res = f.read()
        response=json.loads(res)
        images = [0]*p.num
        p.seedList=[0]*p.num
        s=response["data"][1]
        info=json.loads(s)
        print("seed",info["seed"])

        firstSeed=int(info["seed"])
        if (p.num==1):
            data = response["data"][0][0] # first image
            p.seedList[0]=str(int(firstSeed))
            images[0]=base64ToQImage(data)
        else:
            for i in range(0,p.num):
                data = response["data"][0][i+1] # first image
                p.seedList[i]=str(int(firstSeed)+i)
                images[i]=base64ToQImage(data)
        if (p.imageDialog):                 # only refresh image
            if (p.regenerate):
                print("generate new")
                p.imageDialog.updateImages(images,p.seedList)
            else:  
                p.imageDialog.updateImage(images[0])
        return images
    except  Exception as e:
            error_message = traceback.format_exc() 
            errorMessage("Couldn't connect to server","Unable to make connection to "+endpoint+", Reason: "+error_message)
            return False

def getDocument():
    d = Application.activeDocument()
    if (d==None):  errorMessage("Please add a document","Needs document with a layer and selection.")
    return d

def getLayer():
    d=getDocument()
    if (d==None):  return
    n = d.activeNode()
    return n

def getSelection():
    d = getDocument()
    if (d==None): return
    s = d.selection()
    if (s==None):  errorMessage("Please make a selection","Operation runs on a selection only. Please use rectangle select tool.")
    return s      

def getFullPrompt(dlg):
    modifiers=dlg.modifiers.toPlainText().replace("\n", ", ")
    prompt=dlg.prompt.text()
    if (not prompt):      
        errorMessage("Empty prompt","Type some text in prompt input box about what you want to see.")
        return ""
    prompt+=", "+modifiers
    return prompt

def TxtToImage():
    s=getSelection()
    if (s==None):   return   
    SDConfig.load(SDConfig)
    dlg = SDDialog("txt2img",None)
    dlg.resize(700,200)
    if dlg.exec():
        dlg.setDlgData()
        p = SDParameters()
        p.prompt=getFullPrompt(dlg)
        if not p.prompt: return        
        p.mode="txt2img"
        data=SDConfig.dlgData
        p.steps=data["steps"]
        p.seed=data["seed"]
        p.num=data["num"]
        p.sampling_method=data["sampling_method"]
        p.cfg_value=data["cfg_value"]
        images = asyncio.run(runSD(p))
        imageResultDialog( images,p)


def ImageToImage():
    s=getSelection()
    if (s==None):   return    
    n=getLayer()     
    data=n.pixelData(s.x(),s.y(),s.width(),s.height())
    image=QImage(data.data(),s.width(),s.height(),QImage.Format_RGBA8888).rgbSwapped()
    if (s.width()>512 or s.height()>512):   # max 512x512
        image = image.scaled(512,512, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    print(image.width(),image.height())
    data = QByteArray()
    buf = QBuffer(data)
    image.save(buf, 'PNG')
    ba=data.toBase64()
    DataAsString=str(ba,"ascii")
    image64 = "data:image/png;base64,"+DataAsString
    
    dlg = SDDialog("img2img",image)
    dlg.resize(900,200)

    if dlg.exec():
        dlg.setDlgData()
        p = SDParameters()
        p.prompt=getFullPrompt(dlg)
        if not p.prompt: return
        data=SDConfig.dlgData
        p.mode="img2img"
        p.steps=data["steps"]
        p.seed=data["seed"]
        p.num=data["num"]
        p.cfg_value=data["cfg_value"]
        p.image64=image64
        p.strength=data["strength"]
        images = asyncio.run(runSD(p))
        imageResultDialog( images,p)


def Inpainting():    
    n = getLayer()
    if (n==None):  return    
    s=getSelection()
    if (s==None):   return
    data=n.pixelData(s.x(),s.y(),s.width(),s.height())
    image=QImage(data.data(),s.width(),s.height(),QImage.Format_RGBA8888).rgbSwapped()

    image = image.scaled(512,512, Qt.KeepAspectRatio, Qt.SmoothTransformation)        # not using config here
    print(image.width(),image.height())        
    data = QByteArray()
    buf = QBuffer(data)
    image.save(buf, 'PNG')
    ba=data.toBase64()
    DataAsString=str(ba,"ascii")
    image64 = "data:image/png;base64,"+DataAsString
    
    maskImage=QPixmap(image.width(), image.height()).toImage()
    maskImage = maskImage.convertToFormat(QImage.Format_ARGB32)
    # generate mask image
    maskImage.fill(QColor(Qt.black).rgb())
    foundTrans=False
    foundPixel=False
    for i in range(image.width()):
        for j in range(image.height()):
            rgb = image.pixel(i, j)
            alpha = qAlpha(rgb)
            if (alpha !=255):
                foundTrans=True
                maskImage.setPixel(i, j, QColor(Qt.white).rgb())
            else: foundPixel=True

    if (foundTrans==False):
        errorMessage("No transparent pixels found","Needs content with part removed by eraser (Brush in Tool palette + Right click for Eraser selection)")
        return
    if (foundPixel==False):
        errorMessage("No  pixels found","Maybe wrong layer selected? Choose one with some content n it.")
        return        
    data = QByteArray()
    buf = QBuffer(data)
    maskImage.save(buf, 'PNG')
    ba=data.toBase64()
    DataAsString=str(ba,"ascii")
    maskImage64 = "data:image/png;base64,"+DataAsString
    SDConfig.load(SDConfig)
    image = image.scaled(380,380, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # preview smaller
    dlg = SDDialog("inpainting",image)
    dlg.resize(900,200)

    if dlg.exec():
        dlg.setDlgData()
        p = SDParameters()
        p.prompt=getFullPrompt(dlg)
        if not p.prompt: return        
        data=SDConfig.dlgData
        p.mode="inpainting"
        p.steps=data["steps"]
        p.seed=data["seed"]
        p.num=data["num"]
        p.cfg_value=data["cfg_value"]
        p.image64=image64
        p.maskImage64=maskImage64
        images = asyncio.run(runSD(p))
        imageResultDialog( images,p)

# config dialog
def Config():
    dlg=SDConfigDialog()
    if dlg.exec():
        dlg.save()

# expand selection to max size        
def expandSelection():
    d = getDocument()
    if (d==None): return
    s = d.selection()    
    if (not s):  x=0;y=0
    else: x=s.x(); y=s.y()     
    s2 = Selection()    
    s2.select(x, y, SDConfig.width, SDConfig.height, 1)
    d.setSelection(s2)
    d.refreshProjection()


#Inpainting()
#TxtToImage()
#ImageToImage()
#Config()
#expandSelection()
