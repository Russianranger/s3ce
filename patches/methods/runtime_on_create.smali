.method protected onCreate(Landroid/os/Bundle;)V
    .locals 4

    .prologue
    const/16 v2, 0x400

    const-string v3, "AirplayActivity"

    .line 44
    const-string v0, "AirplayActivity"

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "XXX onCreate XXX: "

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v3, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 45
    invoke-super {p0, p1}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V

    .line 47
    const/4 v0, 0x1

    invoke-virtual {p0, v0}, Lcom/ideaworks3d/airplay/AirplayActivity;->requestWindowFeature(I)Z

    .line 48
    invoke-virtual {p0}, Lcom/ideaworks3d/airplay/AirplayActivity;->getWindow()Landroid/view/Window;

    move-result-object v0

    invoke-virtual {v0, v2, v2}, Landroid/view/Window;->setFlags(II)V

    .line 50
    const-string v0, "AirplayActivity"

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "XXX onCreate: "

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {p0}, Lcom/ideaworks3d/airplay/AirplayActivity;->getRequestedOrientation()I

    move-result v1

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v3, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 52
    const-string v0, "sensor"

    invoke-virtual {p0, v0}, Lcom/ideaworks3d/airplay/AirplayActivity;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v0

    check-cast v0, Landroid/hardware/SensorManager;

    iput-object v0, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_SensorManager:Landroid/hardware/SensorManager;

    # S3CE: a restored Main can bypass GameBootActivity after process death.
    invoke-static {p0}, Lcom/ideaworks3d/thesims3/GameBootActivity;->prepareMain(Landroid/app/Activity;)Z

    move-result v0

    if-eqz v0, :s3ce_runtime_not_ready

    .line 53
    const/4 v0, 0x0

    invoke-virtual {p0, v0}, Lcom/ideaworks3d/airplay/AirplayActivity;->createView(Z)V

    :s3ce_runtime_not_ready
    .line 54
    return-void
.end method
