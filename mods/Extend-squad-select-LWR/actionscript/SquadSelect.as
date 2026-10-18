class SquadSelect extends Screen implements IDisposable
{
   var _parent;
   var bIsDisabled;
   var click;
   var delta;
   var helpBarMC;
   var leftBtn;
   var mouseIn;
   var mouseOut;
   var objectiveMC;
   var onPress;
   var release;
   var rightBtn;
   var theSquadList;
   var offset = 0;
   function SquadSelect()
   {
      super();
   }
   function onLoad()
   {
      super.onLoad();
      this.helpBarMC.shouldAnchorToBottom = true;
      this.SetObjective();
      this.UpdateAnchoring();
      Environment.instance().SubscribeToResolutionUpdate(mx.utils.Delegate.create(this,this.UpdateAnchoring));
      var _loc7_ = function()
      {
         if(!this.bIsDisabled)
         {
            this.mouseIn();
         }
      };
      var _loc8_ = function()
      {
         if(!this.bIsDisabled)
         {
            this.click();
         }
      };
      var _loc9_ = function()
      {
         if(!this.bIsDisabled)
         {
            this.release();
            this._parent._parent.scroll(this.delta);
         }
      };
      var _loc10_ = function()
      {
         if(!this.bIsDisabled)
         {
            this.mouseIn();
            this.onPress();
         }
      };
      var _loc11_ = function()
      {
         if(!this.bIsDisabled)
         {
            this.mouseOut();
            this.release();
         }
      };
      var _loc3_ = Bind.movie(this,"selected_unitBrickBg_background","",{});
      _loc3_.setAnchor(7);
      var _loc4_ = Bind.movie(_loc3_,"XComButtonIconPC","leftBtn",{delta:1,style:XComButton.STYLE_HOTLINK_BUTTON,initLabel:"0",_y:-142,_x:-18});
      _loc4_.buttonOnRollOver = _loc7_;
      _loc4_.buttonOnPress = _loc8_;
      _loc4_.buttonOnRelease = _loc9_;
      _loc4_.buttonOnDragOver = _loc10_;
      _loc4_.buttonOnDragOut = _loc11_;
      this.leftBtn = _loc4_;
      var _loc5_ = Bind.movie(this,"selected_unitBrickBg_background","",{});
      _loc5_.setAnchor(9);
      var _loc6_ = Bind.movie(_loc5_,"XComButtonIconPC","rightBtn",{delta:-1,style:XComButton.STYLE_HOTLINK_BUTTON,initLabel:"1",_y:-142,_x:-114});
      _loc6_.buttonOnRollOver = _loc7_;
      _loc6_.buttonOnPress = _loc8_;
      _loc6_.buttonOnRelease = _loc9_;
      _loc6_.buttonOnDragOver = _loc10_;
      _loc6_.buttonOnDragOut = _loc11_;
      this.rightBtn = _loc6_;
   }
   function scroll(delta)
   {
      this.offset += delta;
      var _loc3_ = caurina.transitions.Tweener;
      var _loc4_ = this.theSquadList;
      flash.external.ExternalInterface.call("FlashRaiseMouseEvent",String(_loc4_),Input.MOUSE_UP,String(this) + ".cycle_" + String(delta) + "_" + String(this.offset));
      var maxOffset = 0;
      var _loc5_ = 0;
      while(_loc5_ < _loc4_.unitBoxes.length)
      {
         if(_loc4_.unitBoxes[_loc5_].txtName._visible or _loc4_.unitBoxes[_loc5_].txtAddUnit.text.length > 1)
         {
            maxOffset++;
         }
         _loc5_ = _loc5_ + 1;
      }
      maxOffset = int((maxOffset - 5) / 2);
      if(maxOffset <= 0)
      {
         this.leftBtn._visible = false;
         this.rightBtn._visible = false;
         return undefined;
      }
      if(this.offset == maxOffset)
      {
         this.leftBtn.disable();
      }
      else
      {
         this.leftBtn.enable();
      }
      if(this.offset == - maxOffset)
      {
         this.rightBtn.disable();
      }
      else
      {
         this.rightBtn.enable();
      }
      var _loc6_;
      var _loc7_;
      if(delta != 0)
      {
         _loc3_.removeTweens(_loc4_);
         _loc3_.addTween(_loc4_,{_x:640 + this.offset * 181,time:0.5});
         var sign = delta < 0 ? -1 : 1;
         _loc5_ = 0;
         while(_loc5_ < Math.abs(delta))
         {
            _loc6_ = _loc4_.unitBoxes[5.5 + this.offset + (2.5 - _loc5_) * sign];
            _loc3_.addTween(_loc6_,{onStart:_loc6_.Show,_alpha:100,time:0.5});
            _loc7_ = _loc4_.unitBoxes[5.5 + this.offset - (3.5 + _loc5_) * sign];
            _loc3_.addTween(_loc7_,{onComplete:_loc7_.Hide,_alpha:0,time:0.5});
            _loc5_ = _loc5_ + 1;
         }
      }
      else
      {
         _loc5_ = 0;
         while(_loc5_ < _loc4_.unitBoxes.length)
         {
            if(_loc5_ > 8 + this.offset or _loc5_ < 3 + this.offset)
            {
               _loc4_.unitBoxes[_loc5_].Hide();
            }
            _loc5_ = _loc5_ + 1;
         }
      }
   }
   function UpdateAnchoring()
   {
      this.objectiveMC._x = 0;
      this.objectiveMC._y = 0;
   }
   function SetObjective(title, body)
   {
      var _loc3_ = this.objectiveMC;
      _loc3_.titleText.htmlText = title;
      _loc3_.bodyText.htmlText = body;
      _loc3_._visible = body != "";
   }
}
