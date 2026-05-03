from win32com.client import Dispatch

prog_ids = ['KWPP.Application', 'WPP.Application', 'Kingsoft.WPP.Application']

for pid in prog_ids:
    try:
        app = Dispatch(pid)
        print(f"成功: {pid}")
        app.Quit()
    except Exception as e:
        print(f"失败 {pid}: {e}")