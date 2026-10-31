.method start()V
    # S3CE: one track generation and serialized lifecycle ownership.
    .locals 5

    monitor-enter p0
    :s3ce_try_start
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    if-nez v0, :s3ce_ready
    invoke-direct {p0}, Lcom/ideaworks3d/airplay/SoundPlayer;->init()V
    iget-object v0, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    :s3ce_ready
    const-string v4, "SoundPlayer"
    const-string v1, "starting sound"
    invoke-static {v4, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    iget-object v1, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_SampleData:[S
    iget v2, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_BufSize:I
    div-int/lit8 v2, v2, 0x2
    invoke-direct {p0, v1, v2}, Lcom/ideaworks3d/airplay/SoundPlayer;->generateAudio([SI)V
    iget-object v3, p0, Lcom/ideaworks3d/airplay/SoundPlayer;->m_AudioTrack:Landroid/media/AudioTrack;
    if-ne v0, v3, :s3ce_done
    invoke-virtual {v0}, Landroid/media/AudioTrack;->play()V
    const/4 v3, 0x0
    invoke-virtual {v0, v1, v3, v2}, Landroid/media/AudioTrack;->write([SII)I
    const-string v1, "playing ..."
    invoke-static {v4, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :s3ce_done
    :s3ce_try_end
    monitor-exit p0
    return-void
    .catchall {:s3ce_try_start .. :s3ce_try_end} :s3ce_catchall
    :s3ce_catchall
    move-exception v4
    monitor-exit p0
    throw v4
.end method
