.method protected onStart()V
    .locals 2

    .prologue
    const-string v1, "AirplayActivity"

    .line 87
    const-string v0, "AirplayActivity"

    const-string v0, "XXX onStart XXX"

    invoke-static {v1, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 88
    invoke-super {p0}, Landroid/app/Activity;->onStart()V

    # S3CE: failed startup shows diagnostics without creating a native thread.
    invoke-static {p0}, Lcom/ideaworks3d/thesims3/GameBootActivity;->canStartMain(Landroid/app/Activity;)Z

    move-result v0

    if-eqz v0, :s3ce_runtime_not_ready

    .line 89
    invoke-direct {p0}, Lcom/ideaworks3d/airplay/AirplayActivity;->startAirplay()V

    .line 90
    const-string v0, "AirplayActivity"

    const-string v0, "XXX done onStart XXX"

    invoke-static {v1, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    :s3ce_runtime_not_ready
    .line 91
    return-void
.end method
