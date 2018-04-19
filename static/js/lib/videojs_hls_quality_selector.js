/* Adapted from https://github.com/chrisboustead/videojs-hls-quality-selector .
 * We use our own version rather than the original because
 * the original structures its code in a way that makes it difficult to
 * register the plugin;
 * the original will register the plugin  against its own videojs instance,
 * from its own node_modules, rather than our videojs instance.
 * This happens regardless of whether we 'require' or 'import' it.
 * So, we use our own version instead.
 */

import videojs from "video.js"

const hlsQualitySelector = function() {
  const player = this
  player.ready(() => {
    player.hlsQualitySelector = new HlsQualitySelectorPlugin(player)
  })
}

class HlsQualitySelectorPlugin {
  constructor(player) {
    this.player = player
    this.keyedMenuItems = {}
    this.KEY_FOR_AUTO = "__AUTO__"
    if (this.player.qualityLevels && this.getHls()) {
      this.createQualityMenu()
      this.bindPlayerEvents()
    }
  }

  getHls() {
    return this.player.tech({ IWillNotUseThisInPlugins: true }).hls
  }

  bindPlayerEvents() {
    this.player
      .qualityLevels()
      .on("addqualitylevel", this.onAddQualityLevel.bind(this))
  }

  createQualityMenu() {
    const player = this.player
    const videoJsButtonClass = videojs.getComponent("MenuButton")
    const concreteButtonClass = videojs.extend(videoJsButtonClass, {
      constructor: function() {
        videoJsButtonClass.call(this, player, {
          title: player.localize("Quality")
        })
      },
      createItems: function() {
        return []
      }
    })

    this._qualityMenuButton = new concreteButtonClass()

    const placementIndex = player.controlBar.children().length - 2
    const concreteButtonInstance = player.controlBar.addChild(
      this._qualityMenuButton,
      { componentClass: "qualitySelector" },
      placementIndex
    )
    concreteButtonInstance.addClass("vjs-quality-selector")
    concreteButtonInstance.addClass("vjs-icon-hd")
    concreteButtonInstance.removeClass("vjs-hidden")
  }

  createQualityMenuItem(item) {
    const player = this.player
    const videoJsMenuItemClass = videojs.getComponent("MenuItem")
    const concreteMenuItemClass = videojs.extend(videoJsMenuItemClass, {
      constructor: function() {
        videoJsMenuItemClass.call(this, player, {
          label:      item.label,
          selectable: true,
          selected:   item.selected || false
        })
        this.key = item.key
      },
      handleClick: () => {
        this.selectQualityLevel({ key: item.key })
        this._qualityMenuButton.unpressButton()
      }
    })
    return new concreteMenuItemClass()
  }

  onAddQualityLevel() {
    const player = this.player
    const qualityList = player.qualityLevels()
    const levels = qualityList.levels_ || []

    const menuItems = []
    for (let i = 0; i < levels.length; ++i) {
      const menuItem = this.createQualityMenuItem.call(this, {
        key:   levels[i].id,
        label: `${levels[i].height}p`,
        value: levels[i].height
      })
      menuItems.push(menuItem)
    }
    menuItems.push(
      this.createQualityMenuItem.call(this, {
        key:      this.KEY_FOR_AUTO,
        label:    "Auto",
        value:    "auto",
        selected: true
      })
    )

    if (this._qualityMenuButton) {
      this._qualityMenuButton.createItems = () => menuItems
      this._qualityMenuButton.update()
    }

    this.keyedMenuItems = {}
    for (const menuItem of menuItems) {
      this.keyedMenuItems[menuItem.key] = menuItem
    }
  }

  selectQualityLevel({ key }) {
    for (let i = 0; i < this._qualityMenuButton.items.length; ++i) {
      this._qualityMenuButton.items[i].selected(false)
    }
    const qualityList = this.player.qualityLevels()
    for (let i = 0; i < qualityList.length; ++i) {
      const quality = qualityList[i]
      quality.enabled = quality.id === key || key === this.KEY_FOR_AUTO
    }
    this.keyedMenuItems[key].selected(true)
  }
}

export default hlsQualitySelector
