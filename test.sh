pre_jobs () {
  echo "♻️  Tareas previas en $STACK ..."
  
  ##
  ## AGREGAR DEBAJO TODAS LAS TAREAS EXTRA 
  ## PARA HACER ANTES DE HACER LA COPIA
  ##
  
}


pre_list () {
  echo "♻️  Tareas previas en $STACK ..."
  
  ##
  ## AGREGAR DEBAJO TODAS LAS TAREAS EXTRA 
  ## PARA HACER ANTES DE CREAR LA LISTA
  ##
  
}


post_jobs () {
  echo "♻️  Tareas posteriores en $STACK ..."
  
  ##
  ## AGREGAR DEBAJO TODAS LAS TAREAS EXTRA 
  ## PARA HACER LUEGO DE LA COPIA
  ##
  
  #cp -u ~/docker/syncro/docker-compose.yml $BACKUP_DIR/syncro-compose.yml
  #cp -u ~/docker/util/butler/docker-compose.yml $BACKUP_DIR/butler-compose.yml
  #cp -u ~/docker/notifications/apprise_id $BACKUP_DIR/
}


extra_dirs () {
  echo "♻️  Directorios extra en $STACK ..."
  
  ##
  ## AGREGAR DEBAJO TODAS LAS TAREAS EXTRA 
  ## PARA HACER LUEGO DE RESTAURAR
  ##
  
  #echo "$STACK_DIR/data" >> "$BACKUP_DIR/$STACK.struct"
  #for dir in Dropbox GDrive Mega Onedrive pCloud
  #do
  #    echo "$STACK_DIR/data/$dir" >> "$BACKUP_DIR/$STACK.struct"
  #done
  
}


