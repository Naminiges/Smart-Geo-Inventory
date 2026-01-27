"""
AssetTransfer Model - History pencatatan pemindahan barang
"""
from app import db
from app.models.base import BaseModel


class AssetTransfer(BaseModel):
    """Model untuk mencatat history pemindahan barang antar unit/ruangan"""
    __tablename__ = 'asset_transfers'

    # Barang yang dipindahkan
    item_detail_id = db.Column(db.Integer, db.ForeignKey('item_details.id'), nullable=False)

    # Lokasi ASAL
    from_unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    from_unit_detail_id = db.Column(db.Integer, db.ForeignKey('unit_details.id'), nullable=False)

    # Lokasi TUJUAN
    to_unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    to_unit_detail_id = db.Column(db.Integer, db.ForeignKey('unit_details.id'), nullable=False)

    # Informasi tambahan
    notes = db.Column(db.Text)
    transfer_date = db.Column(db.DateTime, nullable=False)
    transferred_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    item_detail = db.relationship('ItemDetail')
    from_unit = db.relationship('Unit', foreign_keys=[from_unit_id])
    from_unit_detail = db.relationship('UnitDetail', foreign_keys=[from_unit_detail_id])
    to_unit = db.relationship('Unit', foreign_keys=[to_unit_id])
    to_unit_detail = db.relationship('UnitDetail', foreign_keys=[to_unit_detail_id])
    transferred_by_user = db.relationship('User')

    def __repr__(self):
        return f'<AssetTransfer {self.item_detail.serial_number}: {self.from_unit.name} -> {self.to_unit.name}>'
