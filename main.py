from time import perf_counter


from os import makedirs
from pathlib import Path

# from PIL import Image
# from Sprite import Sprite
from SpriteHandler import SpriteHandler
from typing import Optional, Union
import json
import sys

# import util

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
    return QtGui.QBrush(color, pattern)


def make_icon(path: Path) -> QtGui.QIcon:
    return QtGui.QIcon(str(path))


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.root_folders: list[Path] = []
        self.collections: dict[str, bool] = {}
        self.sprite_path: Path = Path("")
        self.base_path: Path = Path(__file__).parent
        self.output_path: Path = Path(__file__).parent
        self.sprite_handler = SpriteHandler()

        self.brushes = (
            make_brush(QtCore.Qt.GlobalColor.red),
            make_brush(QtCore.Qt.GlobalColor.green),
        )
        self.icons = (
            make_icon(self.base_path.joinpath("resources", "xicon.png")),
            make_icon(self.base_path.joinpath("resources", "checkicon.png")),
        )

        self.setupUi(self)
        self.recover_saved_state()

    def add_root_folder(self) -> None:
        fname = QFileDialog.getExistingDirectory(
            self,
            'Select a base level animations folder (e.g. "Knight")',
            str(
                self.sprite_path.resolve()
                if self.sprite_path != Path("")
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

        if not self.root_folders:
            self.sprite_path = selected_path.parent
            self.sprite_handler.sprite_path = self.sprite_path

        elif selected_path.parent != self.sprite_path:
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

        self.root_folders.append(selected_path)
        self.listWidget.addItem(QListWidgetItem(str(selected_path)))
        self.update_saved_state()

    def remove_root_folder(self) -> None:
        self.listWidget.takeItem(self.listWidget.currentRow())
        self.update_saved_state()

    def set_collection_state(self, state: bool) -> None:
        for collection in self.listWidget_2.selectedItems():
            collection_name = collection.text()
            self.sprite_handler.collections[collection_name] = state
            collection.setBackground(self.brushes[state])
            collection.setIcon(self.icons[state])

    def enable_category(self) -> None:
        self.set_collection_state(True)

    def disable_category(self) -> None:
        self.set_collection_state(False)

    def load_categories(self) -> None:
        collections = self.sprite_handler.load_sprite_info(
            Path.joinpath(
                self.sprite_path,
                self.listWidget.item(i).text(),
                "0.Atlases",
                "SpriteInfo.json",
            )
            for i in range(self.listWidget.count())
        )

        self.listWidget_2.clear()
        self.listWidget_2.addItems(collections)
        self.update_collection_states()
        self.infoBox.appendPlainText("Categories loaded.")

    def update_collection_states(self) -> None:
        for collection, enabled in self.sprite_handler.collections.items():
            item = self.listWidget_2.findItems(
                collection, QtCore.Qt.MatchFlag.MatchExactly
            )[0]
            item.setBackground(self.brushes[enabled])
            item.setIcon(self.icons[enabled])

    def load_animations(self) -> None:
        self.listWidget_3.clear()
        self.listWidget_3.addItems(self.sprite_handler.animations)
        self.listWidget_4.clear()
        self.listWidget_3.setCurrentRow(0)
        self.infoBox.appendPlainText("Animations loaded.")

    def animation_changed(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
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
        if current is None:
            return
        self.update_preview(
            str(next(self.sprite_handler.search_sprites(current.text())))
        )

    def pack_sprites(self) -> None:
        self.sprite_handler.load_duplicate_info()
        complete = all(
            self.sprite_handler.check_completion(paths, im_hash)
            for im_hash, paths in self.sprite_handler.duplicates.items()
        )
        if not complete:
            button = QMessageBox.warning(
                self,
                "Some duplicate sprites are not modified",
                "Some duplicate sprites are not modified:\n"
                "This means that a group of duplicates either is all vanilla,"
                "or the non-vanilla sprites do not match. "
                "You can continue if you intentionally left duplicate sprites different / "
                "vanilla. Would you like to continue packing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                defaultButton=QMessageBox.StandardButton.No,
            )
            print(button)
            if button == QMessageBox.StandardButton.No:
                self.infoBox.appendPlainText("Packing cancelled.")
                self.infoBox.repaint()
                return
        self.infoBox.appendPlainText("Packing sprites...")
        self.infoBox.repaint()
        self.animationFilter.setText("")
        self.filter_animations()
        packed = self.sprite_handler.pack_sheets(output_path=self.output_path)
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
        self.update_saved_state()

    def choose_out_folder(self) -> None:
        dirname = QFileDialog.getExistingDirectory(
            self,
            "Select a folder to output packed sprites into",
            "c:\\",
            QFileDialog.Option.ShowDirsOnly,
        )
        if not dirname:
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

        self.lineEdit.setText(dirname)
        self.output_path = path
        self.infoBox.appendPlainText("Output folder selected.")
        self.update_saved_state()

    def update_output_path(self) -> None:
        self.output_path = Path(self.lineEdit.text())
        self.update_saved_state()

    def update_preview(self, new_path: Path) -> None:
        pixmap = QtGui.QPixmap(str(self.sprite_handler.sprite_path.joinpath(new_path)))
        self.spritePreview.setPixmap(pixmap)
        self.spritePreview.setScaledContents(False)
        self.spritePreview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def duplicate_wizard(self) -> None:
        self.infoBox.appendPlainText("Loading all duplicates...")
        self.infoBox.appendPlainText("(This might take a while)")
        self.infoBox.repaint()
        wizard = WizardDialog("", self)
        wizard.exec()

    def animation_duplicates(self) -> None:
        curr = self.listWidget_3.currentItem()
        if curr is None:
            return
        self.infoBox.appendPlainText("Loading animation duplicates...")
        self.infoBox.repaint()
        selected_animation = curr.text()
        self.animationFilter.setText("")
        self.filter_animations()
        wizard = WizardDialog(selected_animation, self)
        wizard.exec()

    def update_autoplay(self, value: int) -> None:
        curr = self.listWidget_4.item(0)
        if value != 2 or curr is None:
            return
        self.playAnimationButton.setEnabled(False)
        self.listWidget_4.setCurrentRow(0)
        QtCore.QTimer.singleShot(80, self.frame_timer)

    def play_animation(self) -> None:
        curr = self.listWidget_4.item(0)
        if self.playAnimationButton.isChecked() or curr is None:
            return
        self.playAnimationButton.setEnabled(False)
        self.listWidget_4.setCurrentRow(0)
        QtCore.QTimer.singleShot(80, self.frame_timer)

    def frame_timer(self) -> None:
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
        query = self.animationFilter.text().casefold()
        for i in range(self.listWidget_3.count()):
            curr_anim = self.listWidget_3.item(i)
            curr_anim.setHidden(query not in curr_anim.text().casefold())
        self.listWidget_4.clear()
        self.listWidget_3.setCurrentRow(0)

    def recover_saved_state(self) -> None:
        save_path = Path.joinpath(Path.home(), "CustomKnight Creator", "savestate.json")
        if not save_path.exists():
            makedirs(save_path.parent, exist_ok=True)
            return
        save_path.touch(exist_ok=True)

        with open(save_path, encoding="utf-8") as f:
            if save_path.stat().st_size == 0:
                return
            save_data = json.load(f)
            if save_data["openFolders"]:
                self.listWidget.addItems(save_data["openFolders"])
                self.sprite_handler.sprite_path = Path(
                    save_data["openFolders"][0]
                ).parent
                self.load_collections()
                # for category in save_data["enabledCategories"]:
                #     self.sprite_handler.collections[category] = save_data[
                #         "enabledCategories"
                #     ][category]
                self.sprite_handler.collections = save_data["enabledCategories"]
                self.update_collection_states()
                self.load_animations()
            if save_data["outputFolder"]:
                self.output_path = Path(save_data["outputFolder"])
                self.lineEdit.setText(save_data["outputFolder"])

    def update_saved_state(self) -> None:
        new_state = json.dumps(
            {
                "openFolders": list(map(str, self.root_folders)),
                "enabledCategories": self.sprite_handler.collections,
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
    def __init__(self, animation: str, parent: MainWindow) -> None:
        super().__init__()
        s = perf_counter()
        self.setupUi(self)
        self.parent = parent
        self.parent.sprite_handler.load_duplicate_info()
        self.duplicates = self.parent.sprite_handler.get_duplicates(animation)
        self.duplicatesWidget.addItems(self.duplicates.keys())
        self.update_frames(self.duplicatesWidget.currentItem(), None)
        self.update_preview(self.listWidget.currentItem(), None)
        self.update_completion()
        t = perf_counter() - s
        print(f"Duplicate wizard initialization took {t:.4f}s.")

    def select_main_copy(self) -> None:
        s = perf_counter()
        curr_dupe_menu = self.duplicatesWidget.currentItem()
        curr_dupe_file = self.listWidget.currentItem()
        if curr_dupe_menu and curr_dupe_file:
            self.parent.sprite_handler.propagate_main_copy(
                curr_dupe_menu.text(), Path(curr_dupe_file.text())
            )
            self.update_completion(self.duplicatesWidget.indexFromItem(curr_dupe_menu))
            self.parent.infoBox.appendPlainText(
                "Duplicates replaced with selected sprite."
            )
        t = perf_counter() - s
        print(f"Select main copy took {t:.4f}s.")

    def autoreplace_all(self) -> None:
        s = perf_counter()
        for i in range(self.duplicatesWidget.count()):
            vanilla_hash = self.duplicatesWidget.item(i).text()
            sprite = self.parent.sprite_handler[
                max(self.duplicates[vanilla_hash], key=lambda p: p.stat().st_mtime)
            ]
            new_hash = str(sprite.image_hash)
            if new_hash != vanilla_hash:
                self.parent.sprite_handler.propagate_main_copy(
                    vanilla_hash, sprite.path
                )
                self.update_completion(i)
        self.parent.infoBox.appendPlainText(
            "All changed sprites have been copied to their duplicates."
        )
        t = perf_counter() - s
        print(f"Autoreplace all took {t:.4f}s.")

    def update_preview(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
        if current is None:
            return
        width = self.preview.width()
        height = self.preview.height()
        pixmap = QtGui.QPixmap(
            str(self.parent.sprite_handler.sprite_path.joinpath(current.text()))
        )
        pixmap = pixmap.scaled(width, height, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.preview.setPixmap(pixmap)
        self.preview.setScaledContents(False)
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def update_frames(
        self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]
    ) -> None:
        if current is None:
            return
        self.listWidget.clear()
        current_item = self.duplicatesWidget.currentItem().text()
        sorted_duplicates = self.parent.sprite_handler.sorted_duplicates(current_item)
        self.listWidget.addItems(map(str, sorted_duplicates))
        self.listWidget.setCurrentRow(0)

    def update_completion(
        self, item_index: Optional[Union[int, QModelIndex]] = None, time=True
    ) -> None:
        if item_index is None:
            s = perf_counter()
            for i in range(self.duplicatesWidget.count()):
                self.update_completion(i, False)
            t = perf_counter() - s
            print(f"Update took {t:.3f} seconds.")
            return None

        if time:
            s = perf_counter()
        if isinstance(item_index, int):
            item = self.duplicatesWidget.item(item_index)
        else:
            item = self.duplicatesWidget.itemFromIndex(item_index)
        current_item = item.text()
        sorted_duplicates = self.parent.sprite_handler.duplicates[current_item]

        complete = self.parent.sprite_handler.check_completion(
            sorted_duplicates, current_item
        )
        item.setBackground(self.parent.brushes[complete])
        item.setIcon(self.parent.icons[complete])

        if time:
            t = perf_counter() - s
            print(f"Single update took {t:.3f} seconds.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
