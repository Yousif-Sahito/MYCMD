"use strict";
const terminal = new Terminal({cursorBlink:true,scrollback:5000,fontSize:14,screenReaderMode:true,
  linkHandler:{activate:()=>{},hover:()=>{},leave:()=>{}},theme:{background:'#111827',foreground:'#f3f4f6'}});
const fit = new FitAddon.FitAddon();
const search = new SearchAddon.SearchAddon();
terminal.loadAddon(fit); terminal.loadAddon(search);
terminal.open(document.getElementById('terminal'));
new QWebChannel(qt.webChannelTransport, channel => {
  const bridge=channel.objects.bridge;
  terminal.onData(data=>bridge.input(data));
  terminal.onResize(size=>bridge.resize(size.cols,size.rows));
  bridge.output.connect(data=>terminal.write(Uint8Array.from(atob(data), c=>c.charCodeAt(0)),()=>bridge.acknowledge()));
  bridge.control.connect(raw=>{
    const c=JSON.parse(raw);
    if(c.action==='clear') terminal.clear();
    if(c.action==='search') search.findNext(c.text);
    if(c.action==='paste') terminal.paste(c.text);
    if(c.action==='copy') bridge.selection(terminal.getSelection());
    if(c.action==='settings') {
      terminal.options.fontSize=c.font_size; terminal.options.scrollback=c.scrollback;
      terminal.options.theme=c.theme==='light'?{background:'#ffffff',foreground:'#172033'}:{background:'#111827',foreground:'#f3f4f6'};
    }
    fit.fit();
  });
  terminal.attachCustomKeyEventHandler(event=>{
    if(event.type==='keydown' && event.ctrlKey && event.shiftKey && event.code==='KeyC') {bridge.selection(terminal.getSelection());return false;}
    if(event.type==='keydown' && event.ctrlKey && event.shiftKey && event.code==='KeyV') {bridge.pasteRequest();return false;}
    return true;
  });
  new ResizeObserver(()=>fit.fit()).observe(document.getElementById('terminal'));
  bridge.ready(); fit.fit(); terminal.focus();
});
