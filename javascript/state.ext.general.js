window.state = window.state || {};
window.state.extensions = window.state.extensions || {};
state = window.state;

function general_ext(tab_name, extension_name, root_container) {

  let container = root_container;
  let store = null;
  let cnTabs = [];
  let root_not_tabs = null;
  let cur_tab_name = tab_name;
  let ext_name = extension_name
  let LS_PREFIX = 'ext-'+ ext_name.replace(" ","-").toLowerCase() + "-"

  function handleToggle() {
    let value = store.get('toggled');
    let toggleBtn = container.querySelector('div.cursor-pointer, .label-wrap');
    //for(let toggleBtn of toggleBtns){
    //if(!toggleBtn){continue}
    if(toggleBtn && toggleBtn.className.split(' ').pop() != "open"){
      if (value && value === 'true') {
        state.utils.triggerEvent(toggleBtn, 'click');
        //load();
      }
      toggleBtn.addEventListener('click', function () {
        let span = this.querySelector('.transition, .icon');
        store.set('toggled', span.style.transform !== 'rotate(90deg)');
        //load();
      });
    }
    //}
  }

  function bindTabEvents() {
    const tabs = container.querySelectorAll('.tabs > div > button');
    tabs.forEach(tab => { // dirty hack here
      tab.removeEventListener('click', onTabClick);
      tab.addEventListener('click', onTabClick);
    });
    return tabs;
  }

  function handleTabs() {
    let tabs = bindTabEvents();
    let value = store.get('tab');
    if (value) {
      for (var i = 0; i < tabs.length; i++) {
        let translations = state.utils.reverseTranslation(tabs[i].textContent)
        if (value in translations) {
        //if (tabs[i].textContent === value) {
          state.utils.triggerEvent(tabs[i], 'click');
          break;
        }
      }
    }
  }

  function onTabClick() {
    store.set('tab', state.utils.reverseTranslation(this.textContent)[0]);
    bindTabEvents();
  }

  function handleCheckbox(checkbox, store) {
    let label = checkbox.nextElementSibling;
    let translations = state.utils.reverseTranslation(label.textContent)
    for (var text of translations){
      var id = state.utils.txtToId(text);
      var value = store.get(id);
      if (value) {break}
    }
    if (value) {
      state.utils.setValue(checkbox, value, 'change');
    }
    checkbox.addEventListener('change', function () {
      let label = checkbox.nextElementSibling;
      let translations = state.utils.reverseTranslation(label.textContent)
      for (var text of translations){
        var id = state.utils.txtToId(text);
        store.set(id, this.checked);
      }
    });
  }
  function handleCheckboxes() {
    let root_checkboxes = root_not_tabs.container.querySelectorAll('input[type="checkbox"]');
    root_checkboxes.forEach(function (root_checkbox) {
      if(cnTabs.length == 0){
        handleCheckbox(root_checkbox, root_not_tabs.store)
      }
      else{
        let needsHandle = true
        for(let tab of cnTabs){
          if(tab.container.contains(root_checkbox)){
            needsHandle = false
            break
          }
        }
        if(needsHandle){handleCheckbox(root_checkbox, root_not_tabs.store)}
      } // else
    });
    
    cnTabs.forEach(({ container, store }) => {
      let checkboxes = container.querySelectorAll('input[type="checkbox"]');
      checkboxes.forEach(function (checkbox) {
        handleCheckbox(checkbox, store)
      });
    });

  }

  function handleTextArea(textarea, index, store) {
    var id = state.utils.txtToId(`textarea_${index}`);
    var value = store.get(id);
    if (value) {
      state.utils.setValue(textarea, value, 'change');
    }
    textarea.addEventListener('change', function () {
      let text = this.value;
      store.set(id, text);
      console.log(`id = ${id}  value = ${text}`)
    });
  }
  function handleTextAreas() {
    let textArea_index = 0; // 因为文本框的顺序不会变，所以命名直接使用序号区分 "textarea_0"
    
    let root_textareas = root_not_tabs.container.querySelectorAll('textarea');
    root_textareas.forEach(function (root_textarea) {
    
      if(cnTabs.length == 0){
        handleTextArea(root_textarea, textArea_index, root_not_tabs.store)
        textArea_index += 1
      }
      else{
        let needsHandle = true
        for(let tab of cnTabs){
          if(tab.container.contains(root_textarea)){
            needsHandle = false
            break
          }
        }
        if(needsHandle){
          handleTextArea(root_textarea, textArea_index, root_not_tabs.store)
          textArea_index += 1
        }
      } // else

    });

    cnTabs.forEach(({ container, store }) => {
      container.querySelectorAll('textarea').forEach(textarea => {
        handleTextArea(textarea, textArea_index, store)
        textArea_index += 1
      });
    });

  }

  function handleSelect(select, store) {
    let translations = state.utils.reverseTranslation(select.querySelector('label').firstChild.textContent)
    for (var text of translations){
      var id = state.utils.txtToId(text);
      var value = store.get(id);
      if (value) {break}
    }
    //id = state.utils.txtToId(translations[0]);
    //if (value) { //前面不需要判断是否有值，因为需要执行handleSelect绑定onchange事件
    state.utils.handleSelect(select, id, store, force=true);
    //}
    if (id === 'preprocessor' && value && value.toLowerCase() !== 'none') {
      state.utils.onNextUiUpdates(handleSliders); // update new sliders if needed
    }
  }
  function handleSelects() {
    
    let root_selects = root_not_tabs.container.querySelectorAll('.gradio-dropdown');
    root_selects.forEach(function (root_select) {
      if(cnTabs.length == 0){
        handleSelect(root_select, root_not_tabs.store)
      }
      else{
        let needsHandle = true
        for(let tab of cnTabs){
          if(tab.container.contains(root_select)){
            needsHandle = false
            break
          }
        }
        if(needsHandle){handleSelect(root_select, root_not_tabs.store)}
      } // else
    });

    cnTabs.forEach(({ container, store }) => {
      container.querySelectorAll('.gradio-dropdown').forEach(select => {
        handleSelect(select, store)
      });
    });

  }

  function handleSlider(slider, store) {
    let label = slider.previousElementSibling.querySelector('label span');
    let translations = state.utils.reverseTranslation(label.textContent)
    for (var text of translations){
      var id = state.utils.txtToId(text);
      var value = store.get(id);
      if (value) {break}
    }
    if (value) {
      state.utils.setValue(slider, value, 'change');
    }
    slider.addEventListener('change', function () {
      //store.set(id, state.utils.reverseTranslation(this.value)[0]);
      let label = slider.previousElementSibling.querySelector('label span');
      let translations = state.utils.reverseTranslation(label.textContent)
      for (var text of translations){
        var id = state.utils.txtToId(text);
        store.set(id, state.utils.reverseTranslation(this.value)[0]);
      }
    });
  }
  function handleSliders() {

    let root_sliders = root_not_tabs.container.querySelectorAll('input[type="range"]');
    root_sliders.forEach(function (root_slider) {
      if(cnTabs.length == 0){
        handleSlider(root_slider, root_not_tabs.store)
      }
      else{
        let needsHandle = true
        for(let tab of cnTabs){
          if(tab.container.contains(root_slider)){
            needsHandle = false
            break
          }
        }
        if(needsHandle){handleSlider(root_slider, root_not_tabs.store)}
      } // else
    });

    cnTabs.forEach(({ container, store }) => {
      let sliders = container.querySelectorAll('input[type="range"]');
      sliders.forEach(function (slider) {
        handleSlider(slider, store)
      });
    });
  }

  function handleRadioButton(fieldset, store) {
    let label = fieldset.firstChild.nextElementSibling;
    let radios = fieldset.querySelectorAll('input[type="radio"]');
    let translations = state.utils.reverseTranslation(label.textContent)
    for (var text of translations){
      var id = state.utils.txtToId(text);
      var value = store.get(id);
      if (value) {break}
    }
    if (value) {
      radios.forEach(function (radio) {
        state.utils.setValue(radio, value, 'change');
      });
    }
    radios.forEach(function (radio) {
      radio.addEventListener('change', function () {
        let label = fieldset.firstChild.nextElementSibling;
        let translations = state.utils.reverseTranslation(label.textContent)
        for (var text of translations){
          var id = state.utils.txtToId(text);
          store.set(id, state.utils.reverseTranslation(this.value)[0]);
        }
      });
    });
  }
  function handleRadioButtons() {

    let root_fieldsets = root_not_tabs.container.querySelectorAll('fieldset');
    root_fieldsets.forEach(function (root_fieldset) {
      if(cnTabs.length == 0){
        handleRadioButton(root_fieldset, root_not_tabs.store)
      }
      else{
        let needsHandle = true
        for(let tab of cnTabs){
          if(tab.container.contains(root_fieldset)){
            needsHandle = false
            break
          }
        }
        if(needsHandle){handleRadioButton(root_fieldset, root_not_tabs.store)}
      } // else
    });

    cnTabs.forEach(({ container, store }) => {
      let fieldsets = container.querySelectorAll('fieldset');
      fieldsets.forEach(function (fieldset) {
        handleRadioButton(fieldset, store)
      });
    });
  }


  function load() {
    setTimeout(function () {
      handleTabs();
      handleCheckboxes();
      handleTextAreas();
      //handleSelects();
      handleSliders();
      handleRadioButtons();
    }, 500);
  }

  function init() {

    store = new state.Store(LS_PREFIX + cur_tab_name);

    if (! container) {
      return;
    }

    let tabs = container.querySelectorAll('.tabitem');
    //console.log(tabs)
    
    cnTabs = [];
    if (tabs.length) {
      tabs.forEach((tabContainer, i) => {
        cnTabs.push({
          container: tabContainer,
          store: new state.Store(LS_PREFIX + cur_tab_name + "_" + i)
        });
      });
    }
    //else {
    root_not_tabs = {
      container: container,
      store: new state.Store(LS_PREFIX + cur_tab_name)
    }
    //}

    handleToggle();
    load();
  }
  return { init,LS_PREFIX };
}


function general_ext_main(tab){

  let cur_tab_name = tab
  let general_ext_obj = undefined
  // 遍历第一级子节点  每个节点选出一个层级最小且innerText不为空的子节点
  function walks_element(element, cur_gen){
    if(element.innerText != "" && element.innerText != undefined && element.children.length == 0){
      return [[element.innerText,cur_gen]]
    }
    let res = []
    for(child of element.children){
      res = res.concat(walks_element(child,cur_gen+1,res))
    }

    return res
  }

  function init() {
    console.log(`------------${cur_tab_name}----init-------`)

    let container = gradioApp().getElementById(cur_tab_name+'_script_container'); // main container

    let extensions_root = container.children
    if(extensions_root.length > 0 && extensions_root[0].className.split(' ')[0] != "gr-group" && extensions_root[0].className.split(' ')[0] != "gradio-group"){
      extensions_root = extensions_root[0].children // webui v1.6.0 版本，UI结构有变更
    }
    //console.log(extensions_root)
    for (child of extensions_root){
      let root_container = child
      res = walks_element(child, 0)
      let min_gen = 99
      let title = undefined
      for(pair of res){
        if(pair[1] < min_gen){
          min_gen = pair[1]
          title = pair[0]
        }
      }
      
      if(title == undefined 
        || title.toLowerCase() == "lightdiffusionflow" // 自己存自己就不用了
      ){continue}

      let translations = state.utils.reverseTranslation(title)
      title = translations[0] // 标题翻译一般只会有一个？
      if(title.toLowerCase() == 'script'){break} // script后面的面板暂时不考虑
      //console.log(title)
      
      reg = /(.+) v[0-9\.]+/
      if(reg.test(title)){title = RegExp.$1} // 匹配 xxx v0.0.0 格式的标题，把后半部分的版本号去掉

      if(title == "ControlNet"){title = "Control Net"} // 兼容旧命名
      
      let ext_name = title.replace(" ","-").toLowerCase()
      console.log(ext_name)
      general_ext(cur_tab_name, ext_name, root_container).init();
    }
    
  }
  return {init}
}

const TABS = ['txt2img', 'img2img'];
for (tab of TABS){
  state.extensions[`${tab}-ext-general`] = general_ext_main(tab);
}

