<?php
	$releases = array("9"  => "Hardy i386",
                          "10" => "Hardy amd64",
                          "11" => "Intrepid i386",
                          "12" => "Intrepid amd64");

	$categories = array("1"  => "Audio Tools",
                            "2"  => "Programmierung",
                            "3"  => "Spiele",
                            "4"  => "Grafik & Design",
                            "5"  => "Heim & Bildung",
                            "6"  => "Info Management",
                            "7"  => "Internet & Netzwerk",
                            "8"  => "Productivity",
                            "9"  => "Wissenschaft & Mathe",
                            "10" => "Systemwerkzeuge",
                            "11" => "Utilities",
                            "12" => "Video Tools");

	$types = array("1" => "Desktop",
                       "2" => "Kommandozeile",
                       "3" => "Server",
                       "4" => "Webbasierend");

	$best = array("GNOME", "KDE");

	function connect($username, $password) {
		$link = mysql_connect('localhost', $username, $password);
		if (!$link) {
			die('No mysql connection possible: ' . mysql_error());
		}
		return $link;
	}

	function checkRequired($required) {
		foreach($required as $req => $empty) {
			if(!isset($_POST[$req]) || (!$empty && trim($_POST[$req])=="")) die($req." not set");
		}
	}

	function query($sql) {
		print "<pre>".htmlentities($sql)."</pre><br/>\n";
		$ret = mysql_query($sql);
		if(!$ret) {
			die('Error: '.mysql_error());
		}
		return $ret;
	}

	if(count($_POST) != 0) {
		if (get_magic_quotes_gpc()) { 
			$_POST = array_map("stripslashes",$_POST); 
			$_GET = array_map("stripslashes",$_GET); 
			$_COOKIE = array_map("stripslashes",$_COOKIE); 
		}
		$required = array("username" => false,
				  "password" => false,
				  "appName" => false,
				  "basename" => false,
				  "category" => false,
				  "atype" => false,
				  "desc" => false,
				  "home" => true,
				  "license" => false,
				  "best" => false,
				  "note" => true,
				  "version" => false,
				  "changelog" => true,
				  "debversion" => false,
				  "uploader" => false);
		checkRequired($required);

/********************************************************************
BEGIN: WRITE TABLE 'gd_app'
********************************************************************/
		$appName = $_POST['appName'];
		$basename = $_POST['basename'];
		$cat_id = $_POST['category'];
		$atype = $_POST['atype'];
		$descr = $_POST['desc'];
		$home = trim($_POST['home'])!="" ? $_POST['home'] : NULL;
		$license = $_POST['license'];
		$best = $_POST['best']!="NULL" ? $_POST['best'] : NULL;
		$note = trim($_POST['note'])!="" ? $_POST['note'] : NULL;

		$addColumns = "";
		$addValues = "";

		if($home != NULL) {
			$addColumns .= ", home";
			$addValues .= ", '".mysql_real_escape_string($home)."'";
		}

		if($best != NULL) {
			$addColumns .= ", best";
			$addValues .= ", '".mysql_real_escape_string($best)."'";
		}

		if($note != NULL) {
			$addColumns .= ", note";
			$addValues .= ", '".mysql_real_escape_string($note)."'";
		}

		$sql = "INSERT INTO
			gd_app
			(name,
			 basename,
			 cat_id,
			 atype,
			 descr,
			 license
			 ".$addColumns.")
			VALUES
			('".mysql_real_escape_string($appName)."',
			 '".mysql_real_escape_string($basename)."',
			 '".mysql_real_escape_string($cat_id)."',
			 '".mysql_real_escape_string($atype)."',
			 '".mysql_real_escape_string($descr)."',
			 '".mysql_real_escape_string($license)."'
			 ".$addValues.");";

		$link = connect($_POST['username'], $_POST['password']);
		mysql_select_db("getdeb", $link);
		query($sql);
/********************************************************************
END: WRITE TABLE 'gd_app'
********************************************************************/


		$sql = "SELECT
			id
			FROM
			gd_app
			WHERE
			name='".mysql_real_escape_string($appName)."';";
		$ret = query($sql);
		// Should never happen because the name is part of the key.
		if(mysql_num_rows($ret)!=1) {
			die("appName is not unique.");
		}

		$row = mysql_fetch_assoc($ret);
		$appID = $row['id'];

/********************************************************************
BEGIN: WRITE TABLE 'gd_app_version'
********************************************************************/

		$version = $_POST['version'];
		$debversion = $_POST['debversion'];
		$changelog = trim($_POST['changelog'])!="" ? $_POST['changelog'] : NULL;
		$uploader = $_POST['uploader'];

		$addColumns = "";
		$addValues = "";

		if($changelog != NULL) {
			$addColumns .= ", changelog";
			$addValues .= ", '".mysql_real_escape_string($changelog)."'";
		}

		$sql = "INSERT INTO
			gd_app_version
			(app_id,
			 version,
			 debversion,
			 uploader
			 ".$addColumns.")
			VALUES
			('".mysql_real_escape_string($appID)."',
			 '".mysql_real_escape_string($version)."',
			 '".mysql_real_escape_string($debversion)."',
			 '".mysql_real_escape_string($uploader)."'
			 ".$addValues.");";
		query($sql);

/********************************************************************
END: WRITE TABLE 'gd_app_version'
********************************************************************/

		$sql = "SELECT
			id
			FROM
			gd_app_version
			WHERE
			app_id='".mysql_real_escape_string($appID)."';";
		$ret = query($sql);
		// Should never happen because the app_id should only be once in the table at that time
		if(mysql_num_rows($ret)!=1) {
			die("verID is not unique.");
		}

		$row = mysql_fetch_assoc($ret);
		$verID = $row['id'];

/********************************************************************
BEGIN: WRITE TABLE 'gd_app_release'
********************************************************************/

		foreach($releases as $id => $release) {
			if(isset($_POST['release_'.$id]) && $_POST['release_'.$id]==$id) {
				$required = array("release_".$id."_menu" => true,
						  "release_".$id."_command" => true);
				checkRequired($required);

				$menu = trim($_POST['release_'.$id.'_menu'])!="" ? $_POST['release_'.$id.'_menu'] : NULL;
				$command = trim($_POST['release_'.$id.'_command'])!="" ? $_POST['release_'.$id.'_command'] : NULL;

				$addColumns = "";
				$addValues = "";

				if($menu != NULL) {
					$addColumns .= ", menu";
					$addValues .= ", '".mysql_real_escape_string($menu)."'";
				}

				if($command != NULL) {
					$addColumns .= ", command";
					$addValues .= ", '".mysql_real_escape_string($command)."'";
				}

				echo "<b>".$release."</b><br/>\n";
				$sql = "INSERT INTO
					gd_app_release
					(ver_id,
					 distro_id,
					 rdate
					 ".$addColumns.")
					VALUES
					('".mysql_real_escape_string($verID)."',
					 '".mysql_real_escape_string($id)."',
					 NOW()
					 ".$addValues.");";
				query($sql);
			}
		}

/********************************************************************
END: WRITE TABLE 'gd_app_release'
********************************************************************/


/********************************************************************
BEGIN: WRITE TABLE 'gd_app_file'
********************************************************************/

		foreach($releases as $id => $release) {
			if(isset($_POST['release_'.$id]) && $_POST['release_'.$id]==$id) {
				$required = array("release_".$id."_files" => false);
				checkRequired($required);

				$files = trim($_POST['release_'.$id.'_files'])!="" ? $_POST['release_'.$id.'_files'] : NULL;

				echo "<b>".$release." files</b><br/>\n";

				$files_array = explode("\r\n", $files);
				echo "<pre>\n";
				var_dump($files_array);
				echo "</pre>\n";

				// First find the release ID
				$sql = "SELECT
					id
					FROM
					gd_app_release
					WHERE
					distro_id='".$id."' and ver_id='".$verID."';";
				$ret = query($sql);
				// Should never happen
				if(mysql_num_rows($ret)!=1) {
					die("releaseID is not unique.");
				}
				$row = mysql_fetch_assoc($ret);
				$releaseID = $row['id'];

				foreach($files_array as $fpos => $filename) {
					$sql = "INSERT INTO
						gd_app_file
						(rel_id,
						 fpos,
						 name)
						VALUES
						('".$releaseID."',
						 '".$fpos."',
						 '".$filename."');";
					query($sql);
				}
			}
		}

/********************************************************************
END: WRITE TABLE 'gd_app_file'
********************************************************************/


		mysql_close($link);
		// If we got this far. Everything is ok.
		die("<br/><br/><b>Application created successfully.</b><br/><a href=\"http://www.getdeb.net/update_fs.php\">Check files</a><br/>\n");
	}
?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Create package</title>
<meta http-equiv="Content-type" content="text/html;charset=UTF-8" />
</head>


<body>

<form method="post" action="<?= $_SERVER['PHP_SELF'] ?>">
<table border="0" cellpadding="2" cellspacing="0">
	<tr>
		<td><label for="username">mySQL username:</label></td>
		<td><input id="username" name="username" type="text" maxlength="40" /></td>
	</tr>
	<tr>
		<td><label for="password">mySQL password:</label></td>
		<td><input id="password" name="password" type="password" /></td>
	</tr>
	<tr>
		<td><label for="appName">Name:</label></td>
		<td><input id="appName" name="appName" type="text" maxlength="40" /></td>
	</tr>
	<tr>
		<td><label for="basename">Basename:</label></td>
		<td><input id="basename" name="basename" type="text" maxlength="30" /></td>
	</tr>
	<tr>
		<td><label for="category">Category:</label></td>
		<td>
			<select id="category" name="category">
<?php
			foreach($categories as $id => $category) {
				print "<option value=\"".$id."\">".htmlentities($category)."</option>\n";
			}
?>
			</select>
		</td>
	</tr>
	<tr>
		<td><label for="atype">Type:</label></td>
		<td>
			<select id="atype" name="atype">
<?php
			foreach($types as $id => $type) {
				print "<option value=\"".$id."\">".htmlentities($type)."</option>\n";
			}
?>
			</select>
		</td>
	</tr>
	<tr>
		<td><label for="desc">Description:</label></td>
		<td><textarea id="desc" name="desc" cols="50" rows="10"></textarea></td>
	</tr>
	<tr>
		<td><label for="home">Homepage:</label></td>
		<td><input id="home" name="home" type="text" maxlength="128" /></td>
	</tr>
	<tr>
		<td><label for="license">License:</label></td>
		<td><input id="license" name="license" type="text" maxlength="60" /></td>
	</tr>
	<tr>
		<td><label for="best">Best:</label></td>
		<td>
			<select id="best" name="best">
				<option value="NULL">Nothing</option>
<?php
			foreach($best as $b) {
				print "<option>".htmlentities($b)."</option>\n";
			}
?>
			</select>
		</td>
	</tr>
	<tr>
		<td><label for="note">Note:</label></td>
		<td><textarea id="note" name="note" cols="50" rows="10"></textarea></td>
	</tr>
	<tr>
		<td><label for="version">Version:</label></td>
		<td><input id="version" name="version" type="text" maxlength="20" /></td>
	</tr>
	<tr>
		<td><label for="changelog">Changelog:</label></td>
		<td><textarea id="changelog" name="changelog" cols="50" rows="10"></textarea></td>
	</tr>
	<tr>
		<td><label for="debversion">Debversion:</label></td>
		<td><input id="debversion" name="debversion" type="text" maxlength="30" /></td>
	</tr>
	<tr>
		<td><label for="uploader">Uploader:</label></td>
		<td><input id="uploader" name="uploader" type="text" maxlength="40" /></td>
	</tr>
	<tr>
		<td colspan="2">
<?php
	foreach($releases as $id => $release) {
		print "<table border=\"0\" cellpadding=\"2\" cellspacing=\"0\" style=\"border: 1px solid #000000\">\n";
		print "<tr>\n";
		print "<td><label for=\"release_".$id."\">".htmlentities($release).":</label></td>\n";
		print "<td>\n";
		print "<input id=\"release_".$id."\" name=\"release_".$id."\" type=\"checkbox\" value=\"".$id."\" />\n";
		print "</td>\n";
		print "</tr>\n";

		print "<tr>\n";
		print "<td><label for=\"release_".$id."_menu\">Menu:</label></td>\n";
		print "<td>\n";
		print "<input id=\"release_".$id."_menu\" name=\"release_".$id."_menu\" type=\"text\" maxlength=\"128\" />\n";
		print "</td>\n";
		print "</tr>\n";

		print "<tr>\n";
		print "<td><label for=\"release_".$id."_command\">Command:</label></td>\n";
		print "<td>\n";
		print "<input id=\"release_".$id."_command\" name=\"release_".$id."_command\" type=\"text\" maxlength=\"64\" />\n";
		print "</td>\n";
		print "</tr>\n";

		print "<tr>\n";
		print "<td><label for=\"release_".$id."_files\">Files:</label></td>\n";
		print "<td>\n";
		print "<textarea id=\"release_".$id."_files\" name=\"release_".$id."_files\" cols=\"50\" rows=\"4\"></textarea>\n";
		print "</td>\n";
		print "</tr>\n";

		print "</table>\n";
	}
?>
		</td>
	</tr>
	<tr>
		<td colspan="2"><input name="submit" type="submit" /></td>
	</tr>
</table>
</form>

  <p>
    <a href="http://validator.w3.org/check?uri=referer"><img
        src="http://www.w3.org/Icons/valid-xhtml10"
        alt="Valid XHTML 1.0 Transitional" height="31" width="88" /></a>
  </p>

</body>
</html>