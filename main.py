"""
This module implements the user interface functionality for CustomKnight Creator.
"""
from os import makedirs
from pathlib import Path
from spritehandler import SpriteHandler
from typing import Callable, Optional, Union, cast
import json
import sys
import util

from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
)
from PyQt6.QtCore import QModelIndex
from duplicatewizard_ui import Ui_Dialog
from spritepacker_ui import Ui_MainWindow

QtCore.QDir.addSearchPath("resources", "resources")


def make_brush(
    color: QtCore.Qt.GlobalColor,
    pattern: QtCore.Qt.BrushStyle = QtCore.Qt.BrushStyle.Dense4Pattern,
) -> QtGui.QBrush:
    """
    Creates a PyQt brush with the specified color and pattern.

    Parameters
    ----------
    color : QtCore.Qt.GlobalColor
        The brush color.
    pattern : QtCore.Qt.BrushStyle, optional
        The brush pattern. The default is QtCore.Qt.BrushStyle.Dense4Pattern.

    Returns
    -------
    QtGui.QBrush
        A brush that can be used to color PyQt widget backgrounds.

    """
    return QtGui.QBrush(color, pattern)


def make_icon(path: Path) -> QtGui.QIcon:
    """
    Creates an icon object from an image.

    Parameters
    ----------
    path : Path
        The file path to an image to use for the icon.

    Returns
    -------
    QtGui.QIcon
        An icon that can be used for PyQt widgets.

    """
    return QtGui.QIcon(str(path))


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    The MainWindow class implements the main CustomKnight Creator UI window.
    This window provides functionality for Hollow Knight sprite editing.
    Allows for playback and searching of animations, propagation of changed
    sprites to duplicate instances, and spritesheet packing for export and use
    with the CustomKnight mod.
    """

    def __init__(self) -> None:
        """
        Constructor for MainWindow. Initializes the window and loads the last
        saved state, if it exists.

        Returns
        -------
        None.

        """
        # set up PyQt object
        super().__init__()
        self.setupUi(self)

        # attributes for storing data & sprite handler
        self.root_folders: list[str] = []
        self.collections: dict[str, bool] = {}
        self.base_path: Path = Path(__file__).parent
        self.output_path: Path = Path(__file__).parent
        self.sprite_handler = SpriteHandler()

        # graphical elements for indicating enabled/disabled states
        self.brushes = (
            make_brush(QtCore.Qt.GlobalColor.red),
            make_brush(QtCore.Qt.GlobalColor.green),
        )
        self.icons = (
            make_icon(self.base_path.joinpath("resources", "xicon.png")),
            make_icon(self.base_path.joinpath("resources", "checkicon.png")),
        )

        self.recover_saved_state()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """
        Saves current state to disk prior to closing the window.

        Parameters
        ----------
        event : QtGui.QCloseEvent
            Event issued when closing the current window.

        Returns
        -------
        None.

        """
        self.update_saved_state()
        event.accept()

    def add_root_folder(self) -> None:
        """
        Adds a base animation folder to the current list.

        Returns
        -------
        None.

        """
        fname = QFileDialog.getExistingDirectory(
            self,
            'Select a base level animations folder (e.g. "Knight")',
            str(
                self.sprite_handler.sprite_path.resolve()
                if self.sprite_handler.sprite_path != Path("")
                else Path.home()
            ),
            QFileDialog.Option.ShowDirsOnly,
        )
        if not fname:  # user cancelled folder selection dialog
            return

        selected_path = Path(fname)

        if selected_path in self.root_folders:
            QMessageBox.warning(
                self,
                "Duplicate File Selected",
                "Duplicate File Selected:\nPlease select a JSON file not already in the list",
            )
            return

        # set base sprite path if this is first folder to be added
        if not self.root_folders:
            self.sprite_handler.sprite_path = selected_path.parent

        elif selected_path.parent != self.sprite_handler.sprite_path:
            QMessageBox.warning(
                self,
                "Inconsistent Base Path",
                "Inconsistent Base Path:\n"
                "Please make sure all of your top level sprite"
                " folders are in the same directory."
                "(For example, the Knight and Spells Anim"
                " folders should be in the same folder)",
            )
            return

        # add folder
        self.root_folders.append(selected_path.name)
        self.listWidget.addItem(QListWidgetItem(selected_path.name))

    def remove_root_folder(self) -> None:
        """
        Removes a base animation folder from the current list.

        Returns
        -------
        None.

        """
        # pop currently selected folder from list
        taken = self.listWidget.takeItem(self.listWidget.currentRow())

        if taken is not None:
            self.root_folders.remove(taken.text())

    def set_collection_state(self, state: bool) -> None:
        """
        Updates all currently selected collections to a specified state.

        Parameters
        ----------
        state : bool
            True to enable collections, False to disable.

        Returns
        -------
        None.

        """
        for collection in self.listWidget_2.selectedItems():
            collection_name = collection.text()
            self.collections[collection_name] = state
            collection.setBackground(self.brushes[state])
            collection.setIcon(self.icons[state])

    def enable_category(self) -> None:
        """
        Enables all currently selected collections.

        Returns
        -------
        None.

        """
        self.set_collection_state(True)

    def disable_category(self) -> None:
        """
        Disables all currently selected collections.

        Returns
        -------
        None.

        """
        self.set_collection_state(False)

    def load_categories(self) -> None:
        """
        Repopulates collections from open animation folders, setting all
        collections to enabled.

        Returns
        -------
        None.

        """
        self.collections.clear()
        loaded = self.sprite_handler.load_sprite_info(
            Path.joinpath(
                self.sprite_handler.sprite_path,
                self.listWidget.item(i).text(),
                "0.Atlases",
                "SpriteInfo.json",
            )
            for i in range(self.listWidget.count())
        )
        for collection in loaded:
            self.collections[collection] = True

        # update UI to reflect changes
        self.listWidget_2.clear()
        self.listWidget_2.addItems(self.collections)
        self.update_collection_states()
        self.infoBox.appendPlainText("Categories loaded.")

    def update_collection_states(self) -> None:
        """
        Updates displayed collections in the UI to reflect the internal state.

        Returns
        -------
        None.

        """
        for collection, enabled in self.collections.items():
            item = self.listWidget_2.findItems(
                collection, QtCore.Qt.MatchFlag.MatchExactly
            )[0]
            item.setBackground(self.brushes[enabled])
            item.setIcon(self.icons[enabled])

    def load_animations(self) -> None:
        """
        Populates the animation list with animations in enabled categories.

        Returns
        -------
        None.

        """
        self.listWidget_3.clear()
        self.listWidget_3.addItems(
            self.sprite_handler.loaded_animations(self.collections)
        )
        self.listWidget_4.clear()
        self.listWidget_3.setCurrentRow(0)
        self.infoBox.appendPlainText("Animations loaded.")

    def animation_changed(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
        """
        Updates animation frame list upon selecting a different animation.

        Parameters
        ----------
        current : Optional[QListWidgetItem]
            The new animation.
        previous : Optional[QListWidgetItem]
            The old animation.

        Returns
        -------
        None.

        """
        if current is None:
            return
        self.listWidget_4.clear()
        self.listWidget_4.addItems(
            self.sprite_handler.get_animation_sprites(current.text())
        )
        self.listWidget_4.setCurrentRow(0)

    def sprite_changed(
        self, current: Optional[QListWidgetItem], _previous: Optional[QListWidgetItem]
    ) -> None:
        """
        Updates the sprite preview window upon switching to a different sprite.

        Parameters
        ----------
        current : Optional[QListWidgetItem]
            The new sprite to display.
        _previous : Optional[QListWidgetItem]
            The old sprite.

        Returns
        -------
        None.

        """
        if current is None:
            return
        curr_anim = self.listWidget_3.currentItem().text()
        curr_sprite = current.text()
        self.update_preview(
            util.first(self.sprite_handler.search_sprites(curr_anim, curr_sprite))
        )

    def pack_sprites(self) -> None:
        """
        Assembles and saves the sprite sheets for all enabled collections.

        Returns
        -------
        None.

        """
        self.sprite_handler.load_duplicate_info()

        # check if all sets of duplicates are identical and modified
        complete = all(
            self.sprite_handler.check_completion(paths, im_hash)
            for im_hash, paths in self.sprite_handler.duplicates.items()
        )
        if not complete:
            button = QMessageBox.warning(
                self,
                "Some duplicate sprites are not modified",
                "Some duplicate sprites are not modified:\n"
                "This means that a group of duplicates either is all vanilla, "
                "or the non-vanilla sprites do not match. "
                "You can continue if you intentionally left duplicate sprites different / "
                "vanilla. Would you like to continue packing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                defaultButton=QMessageBox.StandardButton.No,
            )
            if button == QMessageBox.StandardButton.No:
                self.infoBox.appendPlainText("Packing cancelled.")
                self.infoBox.repaint()
                return

        # check that all necessary sprites are present, warn otherwise
        mode = self.sprite_handler.DefaultSprite.NONE
        missing = self.sprite_handler.get_missing_root_folders(
            set(self.root_folders), self.collections
        )
        if missing:
            button = QMessageBox.warning(
                self,
                "Not all sprites are loaded",
                "Not all sprites are loaded:\n"
                "This means that a sprite sheet being packed requires sprites "
                "from an unloaded root folder. Proceeding with missing sprites "
                "may lead to blank sprites in the packed sheet or may cause the "
                "sheet to be the wrong size. Would you like to pack using the "
                "vanilla sprite in place of any missing sprites?\n\n"
                "Missing root folders:\n"
                + "\n".join(f"{k}: {', '.join(v)}" for k, v in missing.items()),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.Ignore
                | QMessageBox.StandardButton.Abort,
                defaultButton=QMessageBox.StandardButton.Abort,
            )
            if button == QMessageBox.StandardButton.Abort:
                self.infoBox.appendPlainText("Packing cancelled.")
                return
            elif button == QMessageBox.StandardButton.Yes:
                mode = self.sprite_handler.DefaultSprite.VANILLA
                self.infoBox.appendPlainText("Packing sprites with vanilla default...")
            else:
                self.infoBox.appendPlainText("Packing sprites with no default...")
                self.infoBox.appendPlainText(
                    "(Check that resulting sheets are correctly sized)"
                )
            self.infoBox.repaint()
        else:
            self.infoBox.appendPlainText("Packing sprites...")
            self.infoBox.repaint()

        packed = self.sprite_handler.pack_sheets(
            self.collections, output_path=self.output_path, default_mode=mode,
        )

        # check if all sheets packed properly
        if not packed:
            QMessageBox.warning(
                self,
                "Error Writing Files",
                "Error Writing Files:\n"
                "Please make sure none of the output files are currently open",
            )
            self.infoBox.appendPlainText("Packing failed: file in use.")
        else:
            self.infoBox.appendPlainText("Done packing.")

    def choose_out_folder(self) -> None:
        """
        Updates the spritesheet output directory from a file menu.

        Returns
        -------
        None.

        """
        dirname = QFileDialog.getExistingDirectory(
            self,
            "Select a folder to output packed sprites into",
            "c:\\",
            QFileDialog.Option.ShowDirsOnly,
        )
        if not dirname:  # user cancelled folder selection dialog
            return

        path = Path(dirname)
        if not path.is_dir():
            QMessageBox.warning(
                self,
                "Invalid Output Path",
                "Invalid Output Path:\n"
                "Please select a valid directory to output packed sprites into",
            )
            return

        # update UI and internal output path
        self.output_path = path
        self.lineEdit.setText(dirname)
        self.infoBox.appendPlainText("Output folder selected.")

    def update_output_path(self) -> None:
        """
        Updates the spritesheet output directory on editing the text bar.

        Returns
        -------
        None.

        """
        self.output_path = Path(self.lineEdit.text())

    def update_preview(self, new_path: Path) -> None:
        """
        Displays a new sprite in the preview panel.

        Parameters
        ----------
        new_path : Path
            The path to the sprite to show.

        Returns
        -------
        None.

        """
        pixmap = QtGui.QPixmap(str(self.sprite_handler.sprite_path.joinpath(new_path)))
        self.spritePreview.setPixmap(pixmap)
        self.spritePreview.setScaledContents(False)
        self.spritePreview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def duplicate_wizard(self) -> None:
        """
        Creates a duplicate manager pop-up window for all loaded animations.

        Returns
        -------
        None.

        """
        self.infoBox.appendPlainText("Loading all duplicates...")
        self.infoBox.appendPlainText("(This might take a while)")
        self.infoBox.repaint()
        wizard = WizardDialog("", self)
        wizard.exec()

    def animation_duplicates(self) -> None:
        """
        Creates a duplicate manager pop-up window for the current animation.

        Returns
        -------
        None.

        """
        curr = self.listWidget_3.currentItem()
        if curr is None:  # no animation selected
            return
        self.infoBox.appendPlainText("Loading animation duplicates...")
        self.infoBox.repaint()
        selected_animation = curr.text()
        self.animationFilter.setText("")
        self.filter_animations()
        wizard = WizardDialog(selected_animation, self)
        wizard.exec()

    def update_autoplay(self, value: int) -> None:
        """
        Loops preview of the current animation.

        Parameters
        ----------
        value : int
            The state of the autoplay check box.

        Returns
        -------
        None.

        """
        curr = self.listWidget_4.item(0)
        if value != 2 or curr is None:
            return
        self.playAnimationButton.setEnabled(False)
        self.listWidget_4.setCurrentRow(0)
        QtCore.QTimer.singleShot(80, self.frame_timer)

    def play_animation(self) -> None:
        """
        Plays preview of the current animation once.

        Returns
        -------
        None.

        """
        curr = self.listWidget_4.item(0)
        if self.playAnimationButton.isChecked() or curr is None:
            return
        self.playAnimationButton.setEnabled(False)
        self.listWidget_4.setCurrentRow(0)
        QtCore.QTimer.singleShot(80, self.frame_timer)

    def frame_timer(self) -> None:
        """
        Main driver for animation playback.

        Returns
        -------
        None.

        """
        if self.listWidget_4.item(0) is None:
            return
        if self.listWidget_4.currentRow() + 1 >= self.listWidget_4.count():
            self.listWidget_4.setCurrentRow(0)
            if self.autoplayAnimation.isChecked():
                QtCore.QTimer.singleShot(80, self.frame_timer)
            else:
                self.playAnimationButton.setEnabled(True)
        else:
            self.listWidget_4.setCurrentRow(self.listWidget_4.currentRow() + 1)
            QtCore.QTimer.singleShot(80, self.frame_timer)

    def filter_animations(self) -> None:
        """
        Updates animation list with search results.

        Returns
        -------
        None.

        """
        query = self.animationFilter.text().casefold()

        # set visibility of all loaded animations based on search query
        for i in range(self.listWidget_3.count()):
            curr_anim = self.listWidget_3.item(i)
            curr_anim.setHidden(query not in curr_anim.text().casefold())
        self.listWidget_4.clear()
        self.listWidget_3.setCurrentRow(0)

    def recover_saved_state(self) -> None:
        """
        Loads the saved state from disk and updates the window to match.

        Returns
        -------
        None.

        """
        save_path = Path.joinpath(Path.home(), "CustomKnight Creator", "savestate.json")
        if not save_path.exists():  # no savestate found
            makedirs(save_path.parent, exist_ok=True)
            return
        save_path.touch(exist_ok=True)

        with open(save_path, encoding="utf-8") as f:
            if save_path.stat().st_size == 0:  # empty savestate
                return
            save_data = json.load(f)

            sprite_path = save_data.get("spritePath", None)
            open_folders = save_data.get("openFolders", None)
            enabled = save_data.get("enabledCategories", None)
            out_path = save_data.get("outputFolder", None)

            if sprite_path is not None:
                self.sprite_handler.sprite_path = Path(sprite_path)
            if open_folders:
                self.root_folders = open_folders
                root_paths = util.lmap(Path, open_folders)

                self.listWidget.addItems(p.name for p in root_paths)
                self.load_categories()

                # update enabled/disabled state of loaded collections
                if enabled is not None:
                    self.collections.update(enabled)
                self.update_collection_states()

                self.load_animations()
            if out_path is not None:
                self.output_path = Path(out_path)
                self.lineEdit.setText(out_path)

    def update_saved_state(self) -> None:
        """
        Saves the current state to disk.

        Returns
        -------
        None.

        """
        new_state = json.dumps(
            {
                "spritePath": str(self.sprite_handler.sprite_path),
                "openFolders": util.lmap(str, self.root_folders),
                "enabledCategories": self.collections,
                "outputFolder": str(self.output_path),
            }
        )
        with open(
            Path.joinpath(Path.home(), "CustomKnight Creator", "savestate.json"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(new_state)


class WizardDialog(QDialog, Ui_Dialog):
    """
    The WizardDialog class implements a duplicate sprite manager window for
    CustomKnight Creator. This window allows for overwriting duplicate sprites
    with a selected main copy, or automatic overwriting of all duplicates using
    the most recently modified duplicate sprite.
    """

    def __init__(self, animation: str, parent: MainWindow) -> None:
        """
        Constructor for WizardDialog. Initializes the window and loads detected
        duplicates from selected animations.

        Parameters
        ----------
        animation : str
            The name of the animation to show duplicates of. If `animation` is
            an empty string, loads duplicates from all loaded animations.
        parent : MainWindow
            The main window that created this window.

        Returns
        -------
        None.

        """
        # set up PyQt object
        super().__init__(parent=parent)
        self.setupUi(self)

        # load duplicates
        self.parent: Callable[[], MainWindow] = cast(
            Callable[[], MainWindow], self.parent
        )
        self.parent().sprite_handler.load_duplicate_info()
        self.duplicates = self.parent().sprite_handler.get_duplicates(animation)

        # update UI
        self.duplicatesWidget.addItems(self.duplicates.keys())
        self.update_frames(self.duplicatesWidget.currentItem(), None)
        self.update_preview(self.listWidget.currentItem(), None)
        self.update_completion()

    def select_main_copy(self) -> None:
        """
        Overwrites sprites in the current set of duplicates with the selected
        main copy.

        Returns
        -------
        None.

        """
        curr_dupe_menu = self.duplicatesWidget.currentItem()
        curr_dupe_file = self.listWidget.currentItem()
        if curr_dupe_menu and curr_dupe_file:
            self.parent().sprite_handler.propagate_main_copy(
                curr_dupe_menu.text(), Path(curr_dupe_file.text())
            )

            # update UI
            self.update_completion(self.duplicatesWidget.indexFromItem(curr_dupe_menu))
            self.parent().infoBox.appendPlainText(
                "Duplicates replaced with selected sprite."
            )

    def autoreplace_all(self) -> None:
        """
        Automatically overwrite sprites in all sets of duplicates using the
        most recent sprite in each.

        Returns
        -------
        None.

        """
        for i in range(self.duplicatesWidget.count()):
            vanilla_hash = self.duplicatesWidget.item(i).text()

            # get most recent sprite from current duplicate set
            sprite = self.parent().sprite_handler[
                max(self.duplicates[vanilla_hash], key=lambda p: p.stat().st_mtime)
            ]

            # overwrite other duplicate sprites if non-vanilla
            new_hash = str(sprite.image_hash)
            if new_hash != vanilla_hash:
                self.parent().sprite_handler.propagate_main_copy(
                    vanilla_hash, sprite.path
                )
                self.update_completion(i)
        self.parent().infoBox.appendPlainText(
            "All changed sprites have been copied to their duplicates."
        )

    def update_preview(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
        """
        Updates the sprite preview panel on changing to a different sprite.

        Parameters
        ----------
        current : Optional[QListWidgetItem]
            The new sprite to display.
        previous : Optional[QListWidgetItem]
            The old sprite.

        Returns
        -------
        None.

        """
        if current is None:
            return
        width = self.preview.width()
        height = self.preview.height()
        pixmap = QtGui.QPixmap(
            str(self.parent().sprite_handler.sprite_path.joinpath(current.text()))
        )
        pixmap = pixmap.scaled(width, height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.preview.setPixmap(pixmap)
        self.preview.setScaledContents(False)
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def update_frames(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
        """
        Updates duplicate sprites list upon selecting a different set of
        duplicates.

        Parameters
        ----------
        current : Optional[QListWidgetItem]
            The new group of duplicate sprites.
        previous : Optional[QListWidgetItem]
            The old duplicates.

        Returns
        -------
        None.

        """
        if current is None:
            return
        self.listWidget.clear()
        current_item = self.duplicatesWidget.currentItem().text()
        sorted_duplicates = self.parent().sprite_handler.sorted_duplicates(current_item)
        self.listWidget.addItems(map(str, sorted_duplicates))
        self.listWidget.setCurrentRow(0)

    def update_completion(
        self, item_index: Optional[Union[int, QModelIndex]] = None
    ) -> None:
        """
        Updates the completion status of the currently selected duplicate set.

        Parameters
        ----------
        item_index : Optional[Union[int, QModelIndex]], optional
            The index of the specific duplicate group to update. If `item_index`
            is None, all loaded duplicate groups are checked. The default is None.

        Returns
        -------
        None.

        """
        if item_index is None:  # update all
            for i in range(self.duplicatesWidget.count()):
                self.update_completion(i)
            return None

        # get image hash for duplicate group at given index
        if isinstance(item_index, int):
            item = self.duplicatesWidget.item(item_index)
        else:
            item = self.duplicatesWidget.itemFromIndex(item_index)
        current_item = item.text()

        # check completion status of current group
        sorted_duplicates = self.parent().sprite_handler.duplicates[current_item]
        complete = self.parent().sprite_handler.check_completion(
            sorted_duplicates, current_item
        )

        # update UI to match status
        item.setBackground(self.parent().brushes[complete])
        item.setIcon(self.parent().icons[complete])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
