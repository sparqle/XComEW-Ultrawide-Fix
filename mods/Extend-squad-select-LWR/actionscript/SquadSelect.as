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
   var scrollNotifyTimer;
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
      this.RefreshCardLayout();
   }
   function GetVisibleCardCount()
   {
      var resolution = Environment.instance().resolution;
      if(resolution != undefined && resolution.height > 0 && resolution.width * 9 >= resolution.height * 21)
      {
         return 8;
      }
      return 6;
   }
   function RefreshCardLayout()
   {
      var list = this.theSquadList;
      if(list == undefined || list.unitBoxes == undefined || this.leftBtn == undefined || this.rightBtn == undefined || list.bUpdatingUnits)
      {
         return undefined;
      }
      this.scroll(0);
      if(list.currentSelection >= 0)
      {
         list.SetSelected(list.currentSelection,true);
      }
   }
   function NotifySquadScroll()
   {
      clearTimeout(this.scrollNotifyTimer);
      this.scrollNotifyTimer = undefined;
      flash.external.ExternalInterface.call("FlashRaiseMouseEvent",String(this.theSquadList),Input.MOUSE_UP,String(this) + ".cycle_0_" + String(this.offset));
   }
   function QueueSquadScroll()
   {
      clearTimeout(this.scrollNotifyTimer);
      this.scrollNotifyTimer = setTimeout(mx.utils.Delegate.create(this,this.NotifySquadScroll),1);
   }
   function scroll(delta)
   {
      var list = this.theSquadList;
      if(list.bUpdatingUnits)
      {
         return undefined;
      }
      if(delta == undefined)
      {
         delta = 0;
      }
      var visibleCount = this.GetVisibleCardCount();
      var windowFirst = (list.unitBoxes.length - visibleCount) / 2;
      var windowLast = windowFirst + visibleCount - 1;
      var first = list.unitBoxes.length;
      var last = -1;
      var i = 0;
      while(i < list.unitBoxes.length)
      {
         var box = list.unitBoxes[i];
         if(box.txtName._visible || box.txtAddUnit.text.length > 1)
         {
            first = Math.min(first,i);
            last = i;
         }
         i++;
      }
      var minOffset = 0;
      var maxOffset = 0;
      if(last - first + 1 > visibleCount)
      {
         minOffset = first - windowFirst;
         maxOffset = last - windowLast;
      }
      var oldOffset = this.offset;
      this.offset = Math.max(minOffset,Math.min(maxOffset,oldOffset + delta));
      var moved = this.offset - oldOffset;
      var tweener = caurina.transitions.Tweener;
      tweener.removeTweens(list);
      if(delta != 0 && moved != 0)
      {
         tweener.addTween(list,{_x:640 + this.offset * 181,time:0.5});
      }
      else
      {
         list._x = 640 + this.offset * 181;
      }
      i = 0;
      while(i < list.unitBoxes.length)
      {
         box = list.unitBoxes[i];
         tweener.removeTweens(box);
         if(i >= windowFirst + this.offset && i <= windowLast + this.offset && (box.txtName._visible || box.txtAddUnit.text.length > 1))
         {
            if(delta != 0 && moved != 0 && !box._visible)
            {
               box.Show();
               tweener.addTween(box,{_alpha:100,time:0.5});
            }
            else
            {
               box.Show();
               box._alpha = 100;
            }
         }
         else if(delta != 0 && moved != 0 && box._visible)
         {
            tweener.addTween(box,{onComplete:box.Hide,_alpha:0,time:0.5});
         }
         else
         {
            box.Hide();
            box._alpha = 0;
         }
         i++;
      }
      this.leftBtn._visible = maxOffset > minOffset;
      this.rightBtn._visible = maxOffset > minOffset;
      if(this.offset >= maxOffset)
      {
         this.leftBtn.disable();
      }
      else
      {
         this.leftBtn.enable();
      }
      if(this.offset <= minOffset)
      {
         this.rightBtn.disable();
      }
      else
      {
         this.rightBtn.enable();
      }
      if(delta != 0 && moved != 0)
      {
         clearTimeout(this.scrollNotifyTimer);
         this.scrollNotifyTimer = undefined;
         flash.external.ExternalInterface.call("FlashRaiseMouseEvent",String(list),Input.MOUSE_UP,String(this) + ".cycle_" + String(delta) + "_" + String(this.offset));
      }
      else if(moved != 0)
      {
         this.QueueSquadScroll();
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
