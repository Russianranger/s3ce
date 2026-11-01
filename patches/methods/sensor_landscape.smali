.method private fixOrientation(I)V
    .locals 4

    .prologue
    const/4 v3, 0x1

    .line 220
    iput p1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_FixScreenOrientation:I

    .line 221
    const-string v0, "AirplayThread"

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "fixOrientation: "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    iget v2, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_FixScreenOrientation:I

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 222
    iget v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_FixScreenOrientation:I

    if-ne v0, v3, :cond_0

    .line 223
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Airplay:Lcom/ideaworks3d/airplay/AirplayActivity;

    invoke-virtual {v0, v3}, Lcom/ideaworks3d/airplay/AirplayActivity;->setRequestedOrientation(I)V

    .line 228
    :goto_0
    return-void

    .line 224
    :cond_0
    iget v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_FixScreenOrientation:I

    const/4 v1, 0x2

    if-ne v0, v1, :cond_1

    .line 225
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Airplay:Lcom/ideaworks3d/airplay/AirplayActivity;

    # S3CE Flip3: retain sensor-selected normal/reverse landscape.
    const/4 v1, 0x6

    invoke-virtual {v0, v1}, Lcom/ideaworks3d/airplay/AirplayActivity;->setRequestedOrientation(I)V

    goto :goto_0

    .line 227
    :cond_1
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Airplay:Lcom/ideaworks3d/airplay/AirplayActivity;

    iget v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_OrigScreenOrientation:I

    invoke-virtual {v0, v1}, Lcom/ideaworks3d/airplay/AirplayActivity;->setRequestedOrientation(I)V

    goto :goto_0
.end method
