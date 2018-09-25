#!/bin/python

import xml.sax
import re
import optparse

from tkinter import filedialog, messagebox
from tkinter import *

from enum import Enum

VER=0.1


class errorType(Enum):
    MARKER = 1
    NUMBER = 2
    NAME   = 3

class SisuDataHandler( xml.sax.ContentHandler ):
    def __init__(self):
        self.tagRegexes = [
                        re.compile("%{[a-zA-Z0-9]+}s"),     # %{tag}s
                        re.compile("%\([a-zA-Z0-9]+\)s"),   # %(tag)s
                        re.compile("{[0-9]+}"),             # {0}
                        re.compile("{a-zA-Z0-9]+}")         # {sometag}
                    ]
        self.numberRegexPL = re.compile("[0-9]+( [0-9]{3}){0,}")  # numbers (PL) 
        self.numberRegexEN = re.compile("[0-9]+(,[0-9]{3}){0,}")  # numbers (PL) 
        self.activeRe = None
        self.docuType = None
        self.currentData = None
        self.lang = None
        self.textPL = ""
        self.textEN = ""
        self.rowId = None
        self.report = []

    def startElement(self, tag, attributes):
        self.currentData = tag
        if tag == "source":
            self.docuType = attributes["class"]
        elif tag == "lang":
            self.lang = attributes["id"]
        elif tag == "row":
            self.rowId = attributes["id"]
            
    def endElement(self, tag):
        if tag == "row":
            self.verify()
            self.lang = None
            self.currentData = None
            self.textPL = ""
            self.textEN = ""
            self.rowId = None


    def characters(self, content):
        if self.currentData == "lang":
            if self.lang == "pl":
                self.textPL += content
            elif self.lang == "en":
                self.textEN += content

    ## procedure is called when </row> is found
    # - self.textEN, self.textPL    contain language representations
    #
    def verify(self):
        ### search for markers
        # first attempt to match tag:
        if self.activeRe is None:
            for r in self.tagRegexes:
                if re.search(r, self.textEN):
                    self.activeRe = r
                    self.verify()
                    return
        else:
            for t in re.finditer(self.activeRe, self.textEN.strip()):
               if not re.search(re.escape( t.group() ), self.textPL):
                   self.report.append({'type' : errorType.MARKER,
                                       'id' : self.rowId,
                                       'textEN' : self.textEN.strip(),
                                       'textPL' : self.textPL.strip(),
                                       'tag' : t.group(),
                                       'tagSpanEN' : t.span() } )                  
        ### search for numbers
        mEN = re.search(self.numberRegexEN, self.textEN)
        if mEN:
            sEN = mEN.span()
            try:
                noEN = int(re.sub(",", "", self.textEN[slice(*sEN)]))
            except ValueError:
                noEN = None
            mPL = re.search(self.numberRegexPL, self.textPL)
            if mPL:
                sPL = mPL.span()
                try:
                    noPL = int(re.sub(" ", "", self.textPL[slice(*sPL)]))
                except ValueError:
                    noPL = None
            else:
                sPL = (-1,-1)
            if not mPL or noEN != noPL:
                self.report.append({'type' : errorType.NUMBER,
                                    'id' : self.rowId,
                                    'textEN' : self.textEN.strip(),
                                    'textPL' : self.textPL.strip(),
                                    'tagSpanEN' : sEN,
                                    'tagSpanPL' : sPL } )



                
        # https://stackoverflow.com/questions/18715688/find-common-substring-between-two-strings

    def getReport(self):
        return self.report



class SimpleTable(Frame):

    class TranslationText(Text):
        def __init__(self, parent, text, markerspan):
            Text.__init__(self, parent, width=50, height=3, relief=GROOVE)
            self.insert(END, text)
            self.tag_add('mark', "1."+str(markerspan[0]), "1."+str(markerspan[1]) )
            self.tag_configure('mark', background='yellow', relief='raised')
            self.config(state='disabled')

    class TranslationEntry(Entry):
        def __init__(self, parent, text):
            Entry.__init__(self, parent)
            self.insert(END, text)

    
    def __init__(self, parent, data):
        Frame.__init__(self, parent)
        self.rows = len(data)*2          # double rows for EN and PL strings

        for c,l in enumerate(["Row ID", "Marker", "Strings"]):
            Label(self,text=l).grid(row=0,column=c, stick="nsew")

        rowCnt = 1
        for d in data:
            self.TranslationEntry(self, d['id'] ).grid(row=rowCnt, column=0, stick="new")
            self.TranslationEntry(self, d['tag']).grid(row=rowCnt, column=1, stick="ne")
            self.TranslationText(self , d['textEN'], d['tagSpanEN']).grid(row=rowCnt, column=2, stick="nsew")
            rowCnt+=1
            # two placeholders in grid... 
            for i in range(2):
               Label(self, text="").grid(row=rowCnt, column=i)
            self.TranslationText(self, d['textPL'], (-1,-1)).grid(row=rowCnt, column=2, stick="nsew")
            rowCnt+=1

        # on resize, first and last col stretch the most
        for column, weight in [(0, 2), (1,1), (2,3)]:
            self.grid_columnconfigure(column, weight=weight)

        # last row takes up what's left
        self.grid_rowconfigure(rowCnt-1, weight=1)                
        
        
class ResultsWindow(Frame):
    def __init__(self, parent, results):
        Frame.__init__(self, parent)
        
        # https://stackoverflow.com/questions/16188420/python-tkinter-scrollbar-for-frame
        vscrollbar = Scrollbar(self, orient=VERTICAL)
        vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
        canvas = Canvas(self, bd=0, highlightthickness=0,
                        yscrollcommand=vscrollbar.set)
        canvas.pack(side=TOP, fill=BOTH, expand=TRUE)
        vscrollbar.config(command=canvas.yview)

        # reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        self.interior = interior = SimpleTable(self,results)

        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=NW)
        
        self.quit = Button(self, text="Close", command=parent.destroy)
        self.quit.pack(side="bottom")

        def _configure_interior(event):
                # update the scrollbars to match the size of the inner frame
                size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
                canvas.config(scrollregion="0 0 %s %s" % size)
                if interior.winfo_reqwidth() != canvas.winfo_width():
                    # update the canvas's width to fit the inner frame
                    canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
                if interior.winfo_reqwidth() != canvas.winfo_width():
                    # update the inner frame's width to fill the canvas
                    canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)


def get_version(option, opt, value, parser):
    print("script version:", VER)
    exit(0)


if __name__ == "__main__":

    usage = "usage: %prog [options] arg"
    parser = optparse.OptionParser(usage)
    parser.add_option("-f", "--file", help=".slp file to verify", dest="filename")
    parser.add_option("-g", "--gui", help="run GUI (Tk required)", action="store_true", dest="rungui")
    parser.add_option("--version", help="show script version", action="callback", callback=get_version)
    parser.set_defaults(filename="", rungui=False)
    (opts, args) = parser.parse_args()

    if opts.filename == "":
        if opts.rungui == False:
            print("Filename required in console mode")
            exit(0);
        else:   
            filename = filedialog.askopenfilename(
                initialdir = ".",
                title = "Select file",
                filetypes = (("SiSu files","*.slp"),("all files","*.*"))
                )
        if len(filename) == 0:
            root.quit()
            exit(0)
    else:
        filename = opts.filename

    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    Handler = SisuDataHandler()
    parser.setContentHandler( Handler )
    try: 
        parser.parse(filename)
    except ValueError:
        print("Wrong file name")
        exit(0)
        
    report = Handler.getReport()
    if opts.rungui:
        root = Tk()
        if len(report) == 0:
            messagebox.showinfo(title="Problems in file: "+filename, message="No marker problems found")
            root.quit()
        else:
            root.title("Problems in file: "+filename)
            resWin = ResultsWindow(root,report)
            resWin.pack(side="top", fill="both", expand="true")
            root.mainloop()
    else:
        print("*********************************************")
        print("Found ", str(len(report)), " problems")
        print("*********************************************")
        for d in report:
            if d['type'] == errorType.MARKER:
                print('[ID]\t{0}\n[TAG]\t{1}\n[EN]\t{2}\n[PL]\t{3}'.format(d['id'], d['tag'], d['textEN'], d['textPL']))
            elif d['type'] == errorType.NUMBER:
                print('[ID]\t{0}\n[ER]\t{1}\n[EN]\t{2}\n[PL]\t{3}'.format(d['id'], "number!", d['textEN'], d['textPL']))

            print("*********************************************")

