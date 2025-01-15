


import argparse
import TermTk as ttk

def BuildMainScreen(root=None):

    root_layout = ttk.TTkGridLayout()
    root.setLayout(root_layout)

    btn_frame = ttk.TTkFrame(parent=root)
    btn_layout = ttk.TTkGridLayout()
    btn_frame.setLayout(btn_layout)

    top_btn_frame = ttk.TTkFrame(border=False, maxWidth = 20)
    top_btn_layout = ttk.TTkVBoxLayout()
    top_btn_frame.setLayout(top_btn_layout)


    top_btn_frame.addWidget(ttk.TTkButton(border=True, text="Login", minHeight=3))
    top_btn_frame.addWidget(ttk.TTkButton(border=True, text="Config", minHeight=3))
    top_btn_frame.addWidget(ttk.TTkButton(border=True, text="Service", minHeight=3))    
    top_btn_frame.addWidget(ttk.TTkButton(border=True, text="View", minHeight=3))
    top_btn_frame.addWidget(ttk.TTkButton(border=True, text="Broker", minHeight=3))

    btn_layout.addWidget(top_btn_frame, 1, 0)

    mid_btn_frame = ttk.TTkFrame(border=False)
    btn_layout.addWidget(mid_btn_frame, 2,0)

    bot_btn_frame = ttk.TTkFrame(border=False)
    bot_btn_frame_layout=ttk.TTkVBoxLayout()
    bot_btn_frame.setLayout(bot_btn_frame_layout)
  
    bot_btn_frame_layout.addWidget(ttk.TTkCheckbox(text="Log"))
    bot_btn_frame_layout.addWidget(ttk.TTkButton(border=True, text="Exit", maxHeight = 5))   
    
    btn_layout.addWidget(bot_btn_frame, 5,0) 


    login_frame = ttk.TTkFrame(border=True, title="Login")
    root_layout.addWidget(login_frame, 0, 2)
    login__layout = ttk.TTkVBoxLayout()
    login_frame.setLayout(login__layout)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='Full Screen (default)', action='store_true')
    parser.add_argument('-w', help='Windowed',    action='store_true')
    args = parser.parse_args()
    windowed = args.w
    windowed = False

    root = ttk.TTk(title="GPIO service applicatin")

    if windowed:
        MainWnd = ttk.TTkWindow(parent=root,pos=(1,1), size=(120,40), title="GPIO service applicatin", border=True, layout=ttk.TTkGridLayout())
        border = True
    else:
        root.setLayout(ttk.TTkGridLayout())
        MainWnd = root
        border = False

    BuildMainScreen(MainWnd)
    
    root.mainloop()


if __name__ == "__main__":
    main()    