#!/usr/bin/python
#
#  (C) Copyright 2009, GetDeb Team - https://launchpad.net/~getdeb
#  --------------------------------------------------------------------
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#  --------------------------------------------------------------------
#
#  This file contains the database model

from elixir import *
from sqlalchemy import UniqueConstraint


class PackageList(Entity):
    """
    Identifies a package list, there will be one row for each 
    "Packages" file, the uniqe key is:
        suite+version+component+architecture
    """
    using_options(tablename='packagelist')
    id = Field(Integer, primary_key=True)
    origin = Field(String(64), nullable=False)
    suite = Field(String(64), nullable=False) 
    version = Field(String(64), nullable=False)
    component = Field(String(64), nullable=False)
    architecture = Field(String(64), nullable=False)    
    label = Field(String(64), nullable=False)    
    description = Field(String(128), nullable=True)
    date = Field(String(64), nullable=False)        
    using_table_options(UniqueConstraint('suite', 'version',
        'component', 'architecture'))        
    packages = ManyToMany('Package')
    using_table_options(mysql_engine='InnoDB')
    

    def __repr__(self):
            return '<PackageList "%s %s %s %s %s">' % (self.origin \
                , self.suite, self.version, self.component \
                , self.architecture)


class Package(Entity):
    """
    Package key information, only the package core information 
        package+source+version+architecture
    is kept on this table, additional data goes into package_data
    """
    using_options(tablename='package')
    id = Field(Integer, primary_key=True)
    package = Field(String(64), nullable=False, index = True) 
    source = Field(String(64), nullable=True, index = True)
    version = Field(String(64), nullable=False, index = True)
    architecture = Field(String(64), nullable=False, index = True)
    using_table_options(UniqueConstraint('package', 'version'
        , 'architecture'))
    lists = ManyToMany('PackageList')
    using_table_options(mysql_engine='InnoDB')        
    

    def __repr__(self):
            return '<Package "%s %s %s")>' % (self.package, \
                self.version, self.architecture)


setup_all()


        
"""
class PackageList(Entity):
    using_options(tablename='packagelist')
    id = Field(Integer, primary_key=True)
    archive = Field(String(64), nullable=False) 
    version = Field(String(64), nullable=False)
    component = Field(String(64), nullable=False)
    origin = Field(String(64), nullable=False)
    label = Field(String(64), nullable=False)
    architecture = Field(String(64), nullable=False)
    description = Field(String(128), nullable=False)    
    using_table_options(UniqueConstraint('archive', 'version',
        'component', 'architecture'))
"""









#if __name__ == '__main__':    
    #c1 = RepositoryComponent('jaunty', '9.04', 'apps', 'getdeb', 'getdeb')
    #grant all on apt_portal.* to 'user' identified by 'password';
    #db = create_engine('mysql://user:password@localhost/apt_portal')
    #metadata.create_all(db) 

#PackageList.query.filter_by(archive = archive, version=version, \
#    component=component, origin=origin).one()


#from sqlalchemy import *
#from sqlalchemy.ext.declarative import declarative_base

#Base = declarative_base()

"""
class RepositoryComponent(Base):
    ""
    This class represents a component item the primary key is
    archive-version-component-architecture 
    ""
    __tablename__ = 'component'

    id = Column(Integer, primary_key=True)
    archive = Column(String) 
    version = Column(String)
    component = Column(String)
    origin = Column(String)
    label = Column(String)
    architecture = Column(String)
    description = Column(String)
     
    my_constraint = UniqueConstraint('archive', 'version',
        'component', 'architecture')    
    def __init__(self, archive, version, component, origin, label,
        architecture, description):
        self.archive = archive
        self.version = version
        self.component = component
        self.origin = origin
        self.label = label
        self.architecture = architecture
        self.description = description
    
    #def __repr__(self):
    #    return "<User('%s','%s', '%s')>" % (self.name, self.fullname, self.password)

metadata = MetaData()
packagelist = Table('packagelist', metadata,
    Column('id', Integer, primary_key=True),
    Column('archive', String(64)),
    Column('version', String(64)),
    Column('component', String(64)),
    Column('origin', String(64)),
    Column('lable', String(64)),
    Column('architecture', String(64)),
    Column('description', String(128)),
    UniqueConstraint('archive', 'version',
        'component', 'architecture')
)
"""
