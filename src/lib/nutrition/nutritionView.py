import gtk, gobject
import re, string
from nutritionModel import NutritionModel
import parser_data
import gourmet.cb_extras as cb
import gourmet.dialog_extras as de
import gourmet.convert as convert
from gourmet.defaults import lang as defaults

class NutritionTable:
    """Handed a table (so we can steal it from glade), we pack it full
    of nutritional information."""
    def __init__ (self, table, prefs, default_editable=True):
        self.prefs = prefs
        self.table = table
        self.fields = prefs.get('nutritionFields',
                                # default nutritional fields
                                ['kcal','protein','carb','fiber',
                                 'calcium','iron','sodium',
                                 'fasat','famono','fapoly','cholestrl'])
        self.mnemonics=[]
        self.cells = {}
        self.pack_table()
        self.set_editable(default_editable)
        self.table.show_all()

    def set_nutrition_object (self, obj, multiply_by=None):
        # we want an object that has nutritionFields as attributes.
        # In our metakit-ish world, that means we really are going to
        # be getting a row of our nutrition database as an object, whose
        # attributes represent fields.
        for attr,widgets in self.cells.items():
            val=getattr(obj,attr)
            # if we're multiplying and this is an attribute that needs to be multiplied...
            if multiply_by and attr in parser_data.PER_100_GRAMS:
                val = val * multiply_by
            for w in widgets: w.set_text("%s"%val)

    def set_editable (self, value):
        if value:
            for widgets in self.cells.values():
                widgets[0].show()
                widgets[1].hide()
        else:
            for widgets in self.cells.values():
                widgets[1].show()
                widgets[0].hide()

    def pack_table (self):        
        for n,f in enumerate(self.fields):
            print 'adding field ',n,f
            lname = parser_data.NUT_FIELDNAME_DICT[f]
            label = gtk.Label()
            # we somewhat hackishly attempt to create a mnemonic
            lab = self.create_mnemonic(lname)
            label.set_text_with_mnemonic(lab+":")
            # We might eventually want to make this into SpinButtons, since they
            # are numbers, but I find too many SpinButtons annoying :)
            entr = gtk.Entry()
            label.set_mnemonic_widget(entr)
            lab2 = gtk.Label()
            self.cells[f]=(entr,lab2) # so we can get back at this widget
            self.table.attach(label,0,1,n,n+1)
            self.table.attach(entr,1,2,n,n+1)
            self.table.attach(lab2,2,3,n,n+1)

    def create_mnemonic (self, txt):
        """Create a mnemonic for txt, trying not to use the same
        mnemonic twice."""
        for n,char in enumerate(txt):
            if char.strip() and not char in self.mnemonics:
                self.mnemonics.append(char)
                return txt[0:n]+"_"+txt[n:]
        else:
            # if we must, go ahead and use the same mnemonic twice
            return "_" + txt
                

class NutritionItemView:
    def __init__ (self,
                  nd,
                  usdaChoiceWidget,
                  ingredientWidget,
                  amountWidget,
                  unitChoiceWidget,
                  descChoiceWidget,
                  currentAmountWidget,
                  infoTable,
                  amountLabel=None,
                  unitChoiceLabel=None,
                  descChoiceLabel=None,
                  ):
        self.nd = nd
        self.choices = {}
        self.usdaChoiceWidget=usdaChoiceWidget
        self.ingredientWidget=ingredientWidget
        self.amountWidget = amountWidget
        self.amountLabel = amountLabel
        self.unitChoiceWidget=unitChoiceWidget
        self.descChoiceWidget=descChoiceWidget
        self.currentAmountWidget = currentAmountWidget
        self.unitChoiceLabel=unitChoiceLabel
        self.descChoiceLabel=descChoiceLabel
        #self.ingredientWidget.connect('changed',self.set_ingredient_from_keybox)
        self.usdaChoiceWidget.connect('changed',self.usdaChangedCB)
        self.unitChoiceWidget.connect('changed',self.amountChangedCB)
        self.amountWidget.connect('changed',self.amountChangedCB)
        self.descChoiceWidget.connect('changed',self.amountChangedCB)
        self.infoTable = infoTable
        self.amount=100
        self.unit = 'g.'

    def set_unit_visibility (self, visible):
        if visible:
            self.amountWidget.show()
            self.unitChoiceWidget.show()
            if self.unitChoiceLabel: self.unitChoiceLabel.show()
            if self.amountLabel: self.amountLabel.show()
        else:
            self.unitChoiceWidget.hide()
            self.amountWidget.hide()
            if self.unitChoiceLabel: self.unitChoiceLabel.hide()
            if self.amountLabel: self.amountLabel.hide()
            self.set_desc_visibility(False)
        
    def set_desc_visibility (self, visible):
        if visible:
            self.descChoiceWidget.show()
            if self.descChoiceLabel: self.descChoiceLabel.show()
        else:
            self.descChoiceWidget.hide()
            if self.descChoiceLabel: self.descChoiceLabel.hide()
            
    #def set_ingredient_from_keybox (self,*args):
    #    ing = self.ingredientWidget.get_text()
    #    self.set_ingredient(ing)

    def set_nutref (self, nutrow):
        nutchoices = self.choices.get(self.usdaChoiceWidget) or []
        if nutrow.desc in nutchoices:
            self.set_choice(self.usdaChoiceWidget,nutrow.desc)
        else:
            self.setup_chocies([nutrow.desc]+nutchoices, self.usdaChoiceWidget)
            self.set_choice(nutrow.desc)

    def set_ingredient (self, ing):
        """Handed an ingredient object, we set up our other widgets
        to let the user choose nutritional information."""
        self.ingkey=ing
        self.currentAmountWidget.set_text("%s %s"%(self.amount,self.unit))
        self.setup_usda_choices(ing)
        self.setup_unit_boxes(ing)

    def setup_unit_boxes (self, ing=None, nutrow=None):
        self.densities,self.extra_units = self.nd.get_conversions(row=nutrow,key=ing)
        print 'looking up %s/%s'%(ing,nutrow),' : got densities=',self.densities,' units=',self.extra_units
        self.setup_choices(self.densities.keys(),self.descChoiceWidget)
        units = defaults.WEIGHTS[0:]
        if self.densities: units += defaults.VOLUMES[0:]
        if self.extra_units: units = self.extra_units.keys() + units
        self.setup_choices(units,self.unitChoiceWidget)
        for k in self.densities.keys():
            if k:
                # if we have a key that's not none, then we actually need a descChoiceWidget
                self.setup_choices(self.densities.keys(),self.descChoiceWidget)
                if self.densities.has_key(None):
                    self.set_choice(self.descChoiceWidget,None)
                else:
                    self.set_choice(self.descChoiceWidget,k)
                self.set_desc_visibility(True)
                return
        # if we didn't find any density choices, then we don't need our description widget
        self.set_desc_visibility(False)
        self.setup_choices(None,self.descChoiceWidget)

    def setup_usda_choices (self, ing):
        self.ingkey=ing
        nutrow = self.nd.get_nut_from_key(self.ingkey)
        if nutrow:
            self.choices[self.usdaChoiceWidget]=[nutrow]
            self.setup_choices([nutrow],self.usdaChoiceWidget)
            self.set_choice(self.usdaChoiceWidget,nutrow)
            print 'nutrow already chosen!'
            return
        words=re.split("\W",ing)
        words = filter(lambda w: w and not w in ['in','or','and','with'], words)
        if words:
            # match any of the words in our key
            regexp = "("+string.join(words,"|")+")"
            print 'Filtering nview -- %s items'%len(self.nd.db.nview)
            nvw = self.nd.db.search(self.nd.db.nview,'desc',regexp)
            print 'to %s items'%len(nvw)
            # create a list of rows and sort it, putting the most likely match first
            lst = [[r.desc,r.ndbno] for r in nvw]
            def sort_func (row1,row2):
                dsc1=row1[0].lower()
                dsc2=row2[0].lower()
                sc1=0
                sc2=0
                # we presume recipe keys start with important words and proceed to less
                # important ones -- so we give each word a descending value.
                # in i.e. milk, low fat, we get the points: milk (3), low (2), fat (1)
                score = len(words)
                for w in words:
                    w=w.lower()
                    if dsc1.find(w)>=0: sc1+=score
                    if dsc2.find(w)>=0: sc2+=score
                    score = score - 1
                if sc1<sc2:
                    return 1
                elif sc2<sc1:
                    return -1
                # otherwise, we assume a longer string is a worse match
                elif len(dsc1)>len(dsc2): return 1
                elif len(dsc2)>len(dsc1): return -1
                else: return 0
            print 'sorting list'
            lst.sort(sort_func)
            if len(lst) > 50:
                # we cut down the list if it's too long
                # (so we hope our sorting algorhythm is doing
                # a good job!)
                lst = lst[0:50]
            print 'sorted list and trimmed it to 50 items or fewer'
            self.usdaDict={}
            for l in lst: self.usdaDict[l[0]]=l[1]
            self.choices[self.usdaChoiceWidget]=[x[0] for x in lst]
            #print 'choices are: ',self.choices[self.usdaChoiceWidget]
            self.setup_choices(self.choices[self.usdaChoiceWidget],self.usdaChoiceWidget)
        
    def get_active_usda (self):
        return cb.cb_get_active_text(self.usdaChoiceWidget)

    def get_multiplier (self, *args):
        d=None
        # Grab our density (either the default density for the food, or the density for the
        # user-selected description, such as chopped, sliced, etc).
        if self.densities.has_key(None) or self.densities and self.get_choice(self.descChoiceWidget):
            d=self.densities[self.get_choice(self.descChoiceWidget) or None]
        multiplier=self.nut and self.nd.convert_amount(self.amount,
                                                       self.unit,
                                                       d)
        if multiplier:
            self.set_unit_visibility(False) # if we don't need unit info, don't show it
            return multiplier
        elif self.nut: #if we just need the right unit, see if the user has entered an equivalent...
            # otherwise, we do need unit info, keep it visible
            self.set_unit_visibility(True)
            try:
                amt = convert.frac_to_float(self.amountWidget.get_text())
            except:
                # if there's not a number in Amt, we want to grab it
                print 'no usable amount'
                self.amountWidget.grab_focus()
                return
            else:
                unit = self.get_choice(self.unitChoiceWidget)
                if self.extra_units.has_key(unit):
                    print 'using special unit %s'%unit
                    return self.nd.convert_amount(amt*self.extra_units[unit],'g.')
                else:
                    print 'trying to convert for %s %s %s'%(amt,unit,d)
                    return self.nd.convert_amount(amt,unit,d)

    def usdaChangedCB (self, *args):
        usda_choice = self.get_active_usda()
        ndbno = self.usdaDict[usda_choice]
        self.nut = self.nd.db.nview.select({'ndbno':ndbno})[0]
        self.setup_unit_boxes(nutrow=self.nut)
        self.set_amount()

    def amountChangedCB (self, *args):
        self.set_amount()

    def set_amount (self):
        multiplier = self.get_multiplier()
        if not multiplier:
            #self.unitLabel="%s %s = "%(self.amount,self.unit)
            #self.unitEntry="?"
            print 'we need a unit!'
            self.currentAmountWidget.set_text("%s %s (? grams)"%(self.amount,self.unit))
        else:
            print 'we can convert!'
            self.currentAmountWidget.set_text("%s %s (%s grams)"%(self.amount,self.unit,
                                                                  multiplier*100))            
        self.infoTable.set_nutrition_object(self.nut,multiplier)

    def get_new_conversion (self, *args):
        unit=self.get_choice(self.unitChoiceWidget)
        amt = self.amountWidget.get_text()
        try:
            amt = float(amt)
        except:
            de.show_message(label='Invalid Amount',sublabel='Amount %s is not a number.'%amt)
            self.amountWidget.grab_focus()
        self.amount=amt
        self.unit = unit
        self.usdaChangedCB()

    def setup_choices (self, choices, choiceWidget):
        """Given a list of choices, we setup widget choiceWidget
        to offer those choices to user. By subclassing and overriding
        this method, we can let subclasses use any method they like
        to offer choices

        This function can also be handed None instead of choices, in which
        case there is no meaningful choice for the user to make"""
        print 'setting up choices: choices=',choices,' widget=',choiceWidget
        # make sure there's no current model
        self.choices[choiceWidget]=choices
        choiceWidget.set_model(None)
        if choices:
            cb.set_model_from_list(choiceWidget,choices,expand=False)
        else:
            cb.set_model_from_list(choiceWidget,[None])
        
    def get_choice (self, choiceWidget):
        """Return the user's current choice from choiceWidget"""
        return cb.cb_get_active_text(choiceWidget)

    def set_choice (self, choiceWidget, choice):
        return cb.cb_set_active_text(choiceWidget,choice)


class NutritionCardView:

    """We handle the nutritional portion of our recipe card interface."""

    ING_COL = 0
    NUT_COL = 1
    STR_COL = 2
    
    def __init__ (self, recCard):
        import nutritionGrabberGui        
        self.rc = recCard
        nutritionGrabberGui.check_for_db(self.rc.rg.rd)
        # grab our widgets
        self.treeview = self.rc.glade.get_widget('nutritionTreeView')
        self.treeview.set_property('headers-visible',False)
        self.treeview.set_property('search-column',self.STR_COL)
        #self.expander = self.rc.glade.get_widget('nutritionExpander')
        nutTable = self.rc.glade.get_widget('nutritionTable')
        self.usdaExpander = self.rc.glade.get_widget('usdaExpander')
        self.nutTable = NutritionTable(nutTable,self.rc.prefs)
        self.keyBox = self.rc.glade.get_widget('nutritionKeyBox')
        self.keyBox.entry = self.keyBox.get_children()[0]
        self.usdaCombo = self.rc.glade.get_widget('nutritionUSDACombo')
        self.UnitLabel = self.rc.glade.get_widget('nutUnitLabel')
        self.UnitEntry = self.rc.glade.get_widget('nutUnitEntry')
        self.UnitCombo = self.rc.glade.get_widget('nutUnitCombo')
        self.applyButton = self.rc.glade.get_widget('nutritionApplyButton')
        self.applyButton.connect('clicked',self.applyCB)
        self.customizeButton = self.rc.glade.get_widget('nutritionCustomizeButton')
        self.radioManual = self.rc.glade.get_widget('nutMethod')
        self.radioCalc = self.rc.glade.get_widget('nutMethodCalcButton')
        self.radioUSDA = self.rc.glade.get_widget('nutMethodLookupButton')
        self.radioManual.connect('toggled',self.nutMethodCB)
        self.niv = NutritionItemView(
            self.get_nd(),
            self.usdaCombo,
            self.keyBox.entry,
            self.rc.glade.get_widget('nutAmountEntry'),
            self.UnitCombo,
            self.rc.glade.get_widget('nutDescBox'),
            self.rc.glade.get_widget('nutCurrentUnitLabel'),
            self.nutTable,
            amountLabel=self.rc.glade.get_widget('nutAmountLabel'),
            unitChoiceLabel=self.rc.glade.get_widget('nutUnitLabel'),
            descChoiceLabel=self.rc.glade.get_widget('nutDescLabel'),
            )
        # self.nmodel = NutritionModel(self.rc.ings,self.get_nd()) # no longer use this
        # build our ingredient/nutrition model for our treeview
        self.setup_nmodel()
        self.setup_treeview_columns()
        self.treeview.set_model(self.nmodel)
        # setup treeview callback for selection change
        self.treeviewsel = self.treeview.get_selection()
        self.treeviewsel.set_mode(gtk.SELECTION_SINGLE)
        self.treeviewsel.connect('changed',self.selectionChangedCB)
        self.multiplier = None
        self.nutcombo_set = None

    def setup_nmodel (self):
        # make sure we have an ingredient list
        if not hasattr(self.rc,'ings'):
            self.rc.create_ing_alist()        
        self.nmodel = gtk.ListStore(gobject.TYPE_PYOBJECT,
                                    gobject.TYPE_PYOBJECT,
                                    str)
        self.nmodel.append([None,None,"Recipe"])
        for i in self.rc.ings:
            aliasrow=self.get_nd().get_key(i.ingkey)
            if aliasrow:
                nut_row = self.rc.rg.rd.nview.select({'ndbno':aliasrow.ndbno})
            else:
                nut_row = None
            self.nmodel.append([i,nut_row,i.ingkey])
        

    def setup_treeview_columns (self):
        for n in [self.STR_COL]:
            rend = gtk.CellRendererText()
            col = gtk.TreeViewColumn("",rend,text=n)
            col.set_reorderable(True)
            col.set_resizable(True)
            self.treeview.append_column(col)
        
    def get_nd (self):
        if hasattr(self.rc.rg,'nutritionData'): return self.rc.rg.nutritionData
        else:
            import nutrition
            self.rc.rg.nutritionData = nutrition.NutritionData(self.rc.rg.rd,self.rc.rg.conv)
            return self.rc.rg.nutritionData

    def selectionChangedCB (self, *args):
        mod,itr = self.treeviewsel.get_selected()        
        self.ing=mod.get_value(itr,self.ING_COL)
        self.nut = mod.get_value(itr,self.NUT_COL)        
        if not self.ing or self.nut:
            # then this is the recipe that's been selected!
            self.radioCalc.show()
            self.radioUSDA.hide()
            self.usdaExpander.hide()
            return
        else:
            self.radioCalc.hide()
            self.radioUSDA.show()            
            #if not self.nutcombo_set==self.ing:
            #    self.niv.setup_usda_choices(self.ing.ingkey)
            #    self.nutcombo_set=self.ing
            self.usdaExpander.set_expanded(True)
        if self.nut:
            self.setup_usda_box()            
            self.radioUSDA.set_active(True)
        else:
            self.radioManual.set_active(True)
        self.keyBox.entry.set_text(self.ing.ingkey)        
            
    def setup_usda_box (self):          
        print 'chaging amount and unit: ',self.ing.amount,self.ing.unit        
        self.niv.amount=self.ing.amount
        self.niv.unit=self.ing.unit
        self.niv.set_ingredient(self.ing.ingkey)
        if self.nut:
            self.niv.set_nutref(nutrow)

    def setup_keybox (self, ing):
        self.keyBox.set_model(self.rc.rg.inginfo.key_model.filter_new())
        self.keyBox.set_text_column(0)        
        curkey = self.keyBox.entry.get_text()
        keys = self.rc.rg.rd.key_search(ing.item)
        mod=self.keyBox.get_model()
        if keys:
            def vis (m, iter):
                x = m.get_value(iter,0)
                if x and x in keys: return True
            mod.set_visible_func(vis)
        else:
            mod=set_visible_func(lambda *args: True)
        mod.refilter()
        if len(self.keyBox.get_model()) > 6:
            self.keyBox.set_wrap_width(2)
            if len(self.keyBox.get_model()) > 10:
                self.keyBox.set_wrap_width(3)
        cb.setup_completion(self.keyBox)


    def nutMethodCB (self, widget, *args):
        # our widget is the "manual" widget
        if widget.get_active():
            self.usdaExpander.set_expanded(False)
            self.usdaExpander.set_sensitive(False)
            self.nutTable.set_editable(True)            
        else:
            self.usdaExpander.set_sensitive(True)
            self.setup_usda_box()
            self.usdaExpander.set_expanded(True)
            self.nutTable.set_editable(False)
            
            
    def applyCB (self,*args):
        # ADD SOMETHING HERE TO CALL A "SAVE" type method on our NIV
        # now update our model
        # grab our new conversion
        self.niv.get_new_conversion()
        nmod,itr = self.treeviewsel.get_selected()
        # set our new key
        ing=nmod.get_value(itr,self.ING_COL)
        # (make undoable!)
        #self.rc.rg.rd.undoable_modify_ing(ing,{'ingkey':key},self.rc.history)
        row = self.rc.rg.rd.nview.select({'ndbno':ndbno})[0]
        nmod.set_value(itr,self.NUT_COL,row)
        #nmod.set_value(itr,self.STR_COL,key)

        